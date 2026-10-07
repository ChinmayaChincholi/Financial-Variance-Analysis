import pandas as pd
import pytest

from ingestion.column_matching_pipeline import run_ingestion_on_dataframe
from ingestion.column_profiling import drop_placeholder_or_empty_columns, profile_columns
from ingestion.column_scoring import (
    ScoringWeights,
    resolve_field,
    score_project_candidates,
    score_region_candidates,
)
from ingestion.header_detection import detect_header_row
from ingestion.metric_block_resolver import resolve_metric_blocks
from ingestion.schema import ColumnMapping


# ---------------------------------------------------------------------------
# Header detection
# ---------------------------------------------------------------------------

def test_header_detection_finds_row_below_blank_row():
    raw = pd.DataFrame(
        [
            [None, None, None],
            ["Project", "Region", "Jan 2026"],
            ["Alpha", "India", 100],
            ["Beta", "USA", 200],
        ]
    )
    result = detect_header_row(raw)
    assert result.header_row_index == 1
    assert result.confidence > 0.55


def test_header_detection_ignores_stray_totals_in_row_zero():
    # Mimics Financial_Dataset.xlsx: row 0 is mostly blank except a couple
    # of leftover total numbers under specific columns.
    raw = pd.DataFrame(
        [
            [None, None, 99999.0, None],
            ["Project", "Region", "Amount", "Jan 2026"],
            ["Alpha", "India", -100, 100],
            ["Beta", "USA", -200, 200],
        ]
    )
    result = detect_header_row(raw)
    assert result.header_row_index == 1


# ---------------------------------------------------------------------------
# Project / Region scoring
# ---------------------------------------------------------------------------

def _sample_df():
    return pd.DataFrame(
        {
            "Project Name": ["Alpha", "Alpha", "Beta", "Beta", "Beta", "Gamma"],
            "Resource Name": ["R1", "R2", "R3", "R4", "R5", "R6"],
            "Region": ["India", "India", "USA", "USA", "USA", "Germany"],
            "Jan 2026": [100, 50, 80, 20, 10, 30],
            "Feb 2026": [110, 55, 85, 25, 15, 35],
        }
    )


def test_project_name_scores_highest_among_text_columns():
    df = _sample_df()
    profiles = profile_columns(df)
    scores = score_project_candidates(profiles, df)
    assert scores[0].column == "Project Name"


def test_region_scores_highest_among_text_columns():
    df = _sample_df()
    profiles = profile_columns(df)
    scores = score_region_candidates(profiles)
    assert scores[0].column == "Region"


def test_ambiguous_region_columns_trigger_clarification():
    df = _sample_df().rename(columns={})
    df["Area"] = df["Region"]  # duplicate region-shaped column under a different name
    profiles = profile_columns(df)
    scores = score_region_candidates(profiles)
    resolution = resolve_field(scores, "Region")
    assert resolution.needs_clarification is True
    top_columns = {c.column for c in resolution.candidates}
    assert {"Region", "Area"}.issubset(top_columns)


def test_no_region_like_column_resolves_to_no_candidates():
    df = pd.DataFrame(
        {
            "Project Name": ["Alpha", "Alpha", "Beta"],
            "Jan 2026": [100, 50, 80],
        }
    )
    profiles = profile_columns(df)
    scores = score_region_candidates(profiles)
    assert scores == [] or resolve_field(scores, "Region").resolved_column is None


def test_value_based_candidate_is_not_hidden_by_name_based_candidates():
    # Regression test for a real client scenario: a column named
    # "Company" held country codes and was the column the client's
    # business actually uses for Region -- but it has zero header-text
    # resemblance to "region". Several OTHER columns had strong header
    # matches (Region, Region summary, Sales Region) and previously
    # pushed Company below a fixed top-4 candidate cutoff, silently
    # hiding the correct answer. Company must still appear as a
    # candidate on value evidence (gazetteer overlap) alone.
    n = 40
    df = pd.DataFrame(
        {
            "Project Name": [f"Project {i % 10}" for i in range(n)],
            "Region": (["India", "USA", "Germany", "France"] * (n // 4)),
            "Region summary": (["APAC", "AMER", "EMEA", "EMEA"] * (n // 4)),
            "Sales Region": (["APAC", "AMER", "EMEA", "EMEA"] * (n // 4)),
            "Company": (["India", "USA", "Germany", "France"] * (n // 4)),  # no header signal, real value signal
            "Jan 2026": list(range(n)),
        }
    )
    profiles = profile_columns(df)
    scores = score_region_candidates(profiles)
    resolution = resolve_field(scores, "Region")
    assert resolution.needs_clarification is True
    candidate_columns = {c.column for c in resolution.candidates}
    assert "Company" in candidate_columns, (
        "Company has zero header-text match but strong value-match evidence -- "
        "it must still surface as a candidate, not be truncated out."
    )


# ---------------------------------------------------------------------------
# Metric block resolution
# ---------------------------------------------------------------------------

def test_explicit_revenue_cost_labels_resolve_directly():
    df = pd.DataFrame(
        {
            "Project Name": ["Alpha"],
            "Revenue Jan 2026": [100],
            "Revenue Feb 2026": [110],
            "Cost Jan 2026": [40],
            "Cost Feb 2026": [45],
        }
    )
    profiles = profile_columns(df)
    resolution = resolve_metric_blocks(profiles)
    assert resolution.needs_clarification is False
    assert set(resolution.revenue_cols) == {"Revenue Jan 2026", "Revenue Feb 2026"}
    assert set(resolution.cost_cols) == {"Cost Jan 2026", "Cost Feb 2026"}


def test_neighbor_context_resolves_unlabeled_block():
    df = pd.DataFrame(
        {
            "Project Name": ["Alpha"],
            "Revenue Book currency": [1000],
            "Jan 2026": [100],
            "Feb 2026": [110],
            "YTD Revenue$": [210],
        }
    )
    profiles = profile_columns(df)
    resolution = resolve_metric_blocks(profiles)
    assert resolution.needs_clarification is False
    assert set(resolution.revenue_cols) == {"Jan 2026", "Feb 2026"}
    assert resolution.cost_cols == []


def test_two_unlabeled_blocks_with_no_context_asks_user():
    df = pd.DataFrame(
        {
            "Project Name": ["Alpha"],
            "Jan 2026": [100],
            "Feb 2026": [110],
            "Filler": ["x"],
            "Mar 2026": [40],
            "Apr 2026": [45],
        }
    )
    profiles = profile_columns(df)
    resolution = resolve_metric_blocks(profiles)
    assert resolution.needs_clarification is True
    assert len(resolution.unresolved_blocks) == 2


def test_no_month_year_columns_at_all():
    df = pd.DataFrame({"Project Name": ["Alpha"], "Region": ["India"]})
    profiles = profile_columns(df)
    resolution = resolve_metric_blocks(profiles)
    assert resolution.needs_clarification is True
    assert "No Month-Year columns" in resolution.message


def test_placeholder_unnamed_column_is_not_treated_as_a_month_year_block():
    # Regression test: a near-empty column pandas auto-names "Unnamed: N"
    # (no real header existed in the source file) was found to get
    # fuzzy-date-parsed as a year purely from the trailing number in its
    # name (e.g. "Unnamed: 62" -> year 2062), because
    # parse_month_year_column uses fuzzy=True. Such columns must never
    # reach the point of being considered a Month-Year candidate at all.
    df = pd.DataFrame(
        {
            "Project Name": ["Alpha", "Beta"],
            "Revenue Jan 2026": [100, 80],
            "Unnamed: 62": [None, 1.0],  # 1 real value out of 2 rows -- a stray artifact
        }
    )
    df = drop_placeholder_or_empty_columns(df)
    assert "Unnamed: 62" not in df.columns

    profiles = profile_columns(df)
    resolution = resolve_metric_blocks(profiles)
    assert resolution.needs_clarification is False
    assert resolution.revenue_cols == ["Revenue Jan 2026"]


def test_genuinely_sparse_named_column_is_also_dropped():
    # The fill-ratio check applies independently of the "Unnamed: N"
    # name pattern -- a real-looking header with almost no data should
    # be dropped too, not just pandas's auto-generated placeholders.
    n = 200
    df = pd.DataFrame(
        {
            "Project Name": [f"Project {i}" for i in range(n)],
            "Some Stray Column": [None] * (n - 1) + [1.0],
            "Jan 2026": list(range(n)),
        }
    )
    df = drop_placeholder_or_empty_columns(df)
    assert "Some Stray Column" not in df.columns
    assert "Project Name" in df.columns and "Jan 2026" in df.columns


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def test_full_pipeline_resolves_clean_dataset():
    df = pd.DataFrame(
        {
            "Project Name": ["Alpha", "Alpha", "Beta", "Beta"],
            "Region": ["India", "India", "USA", "USA"],
            "Revenue Jan 2026": [100, 50, 80, 20],
            "Cost Jan 2026": [40, 20, 30, 10],
        }
    )
    result = run_ingestion_on_dataframe(df)
    assert result.status == "resolved"
    mapping = result.column_mapping
    assert mapping.project_col == "Project Name"
    assert mapping.region_col == "Region"
    assert mapping.has_revenue()
    assert mapping.has_cost()


def test_full_pipeline_missing_project_name_requires_clarification():
    df = pd.DataFrame(
        {
            "Region": ["India", "USA"],
            "Revenue Jan 2026": [100, 80],
        }
    )
    result = run_ingestion_on_dataframe(df)
    assert result.status == "needs_clarification"
    fields = {c.field for c in result.clarifications}
    assert "project_name" in fields


def test_full_pipeline_missing_region_is_not_a_clarification():
    # Per spec: Region absent is fine at ingestion time -- it's only
    # surfaced when the user clicks into Region-wise Analysis, not here.
    df = pd.DataFrame(
        {
            "Project Name": ["Alpha", "Beta"],
            "Revenue Jan 2026": [100, 80],
        }
    )
    result = run_ingestion_on_dataframe(df)
    assert result.status == "resolved"
    assert result.column_mapping.region_col is None
    assert result.column_mapping.has_region() is False


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def test_column_mapping_allows_missing_region():
    mapping = ColumnMapping(project_col="Project Name", revenue_month_year_cols=["Jan 2026"])
    assert mapping.region_col is None
    assert mapping.has_region() is False


def test_column_mapping_still_rejects_revenue_cost_overlap():
    with pytest.raises(ValueError):
        ColumnMapping(
            project_col="Project Name",
            revenue_month_year_cols=["Jan 2026"],
            cost_month_year_cols=["Jan 2026"],
        )