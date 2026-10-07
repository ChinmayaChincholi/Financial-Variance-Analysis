"""
Top-level entry point for the NLP/Ingestion layer.

Wires together: header-row detection -> column profiling -> Project/
Region candidate scoring -> Month-Year metric-block resolution -> a
single ColumnMapping (schema.py), OR a list of ClarificationRequests to
surface on the "Confirm Detected Columns" screen (see the UX discussion
in this project's design notes -- automatic detection is always a
pre-filled default the user can see and override, never a silent final
answer).

This module assumes the caller has already resolved which SHEET to use
(the doc's multi-sheet-selection UI is a separate, earlier step -- by
the time run_ingestion() is called, there is exactly one sheet).
"""

import pandas as pd

from ingestion.column_profiling import (
    drop_placeholder_or_empty_columns,
    profile_columns,
)
from ingestion.column_scoring import (
    ScoringWeights,
    resolve_field,
    score_project_candidates,
    score_region_candidates,
)
from ingestion.header_detection import detect_header_row
from ingestion.metric_block_resolver import resolve_metric_blocks
from ingestion.schema import (
    ClarificationRequest,
    ColumnCandidateOut,
    ColumnMapping,
    IngestionResult,
)

HEADER_ROW_CONFIDENCE_FLOOR = 0.55


def _to_candidate_out(candidates) -> list[ColumnCandidateOut]:
    return [
        ColumnCandidateOut(
            column=c.column,
            score=c.score,
            reasons=c.reasons,
            sample_values=c.sample_values,
        )
        for c in candidates
    ]


def _block_label(columns: list[str]) -> str:
    if len(columns) == 1:
        return columns[0]
    return f"{columns[0]} .. {columns[-1]} ({len(columns)} columns)"


def run_ingestion(
        path: str,
        sheet_name: str,
        weights: ScoringWeights = ScoringWeights(),
) -> IngestionResult:
    """
    Runs the full ingestion pipeline against one sheet of an uploaded
    Excel file and returns either a resolved ColumnMapping or the set of
    clarifications needed to build one.

    Parameters
    ----------
    path : path to the uploaded .xlsx file.
    sheet_name : the single sheet to ingest (already chosen by the
        multi-sheet-selection step upstream, if the workbook had more
        than one sheet).
    weights : scoring constants (see column_scoring.ScoringWeights).
    """
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    header_result = detect_header_row(raw)

    if header_result.confidence < HEADER_ROW_CONFIDENCE_FLOOR:
        return IngestionResult(
            status="needs_clarification",
            clarifications=[
                ClarificationRequest(
                    field="header_row",
                    message=(
                        "Couldn't confidently identify which row holds your column "
                        "headers. Please pick the correct row."
                    ),
                    candidates=[
                        ColumnCandidateOut(
                            column=f"Row {r['row_index']}",
                            score=r["score"],
                            sample_values=r["preview"],
                        )
                        for r in header_result.candidate_rows[:5]
                    ],
                )
            ],
            header_row_index=header_result.header_row_index,
            header_row_confidence=header_result.confidence,
        )

    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=header_result.header_row_index,
    )

    return run_ingestion_on_dataframe(
        df,
        weights=weights,
        header_row_index=header_result.header_row_index,
        header_row_confidence=header_result.confidence,
    )


def run_ingestion_on_dataframe(
        df: pd.DataFrame,
        weights: ScoringWeights = ScoringWeights(),
        header_row_index: int | None = None,
        header_row_confidence: float | None = None,
) -> IngestionResult:
    """
    Same as run_ingestion(), but takes an already-loaded DataFrame with
    the correct header applied -- useful for testing, and for the case
    where header-row selection was already resolved via user
    clarification on a previous call.
    """
    df = drop_placeholder_or_empty_columns(df)
    profiles = profile_columns(df)
    clarifications: list[ClarificationRequest] = []

    # --- Project Name ---
    project_scores = score_project_candidates(
        profiles,
        df,
        weights=weights,
    )

    project_resolution = resolve_field(
        project_scores,
        "Project Name",
        weights=weights,
    )

    if project_resolution.needs_clarification:
        clarifications.append(
            ClarificationRequest(
                field="project_name",
                message=project_resolution.message,
                candidates=_to_candidate_out(project_resolution.candidates),
            )
        )

    # --- Region (optional field -- absence is not itself a clarification;
    # only genuine AMBIGUITY between multiple plausible columns is) ---
    region_scores = score_region_candidates(
        profiles,
        weights=weights,
    )

    region_resolution = resolve_field(
        region_scores,
        "Region",
        weights=weights,
    )

    region_col: str | None

    if region_resolution.resolved_column is not None:
        region_col = region_resolution.resolved_column

    elif region_scores and region_resolution.needs_clarification:
        # There WERE candidates, just not a confident/unambiguous one --
        # surface it. A dataset with literally no region-like column at
        # all (empty region_scores) is fine; region_col simply stays None.
        clarifications.append(
            ClarificationRequest(
                field="region",
                message=region_resolution.message,
                candidates=_to_candidate_out(region_resolution.candidates),
            )
        )
        region_col = None

    else:
        region_col = None

    # --- Revenue / Cost Month-Year blocks ---
    metric_resolution = resolve_metric_blocks(profiles)

    if metric_resolution.needs_clarification:
        block_candidates = [
            ColumnCandidateOut(
                column=_block_label(b.columns),
                score=0.0,
                reasons=b.reasons,
                sample_values=[],
            )
            for b in metric_resolution.unresolved_blocks
        ]

        clarifications.append(
            ClarificationRequest(
                field="revenue_or_cost_month_year",
                message=metric_resolution.message,
                candidates=block_candidates,
            )
        )

    if clarifications:
        return IngestionResult(
            status="needs_clarification",
            clarifications=clarifications,
            header_row_index=header_row_index,
            header_row_confidence=header_row_confidence,
        )

    mapping = ColumnMapping(
        project_col=project_resolution.resolved_column,
        region_col=region_col,
        revenue_month_year_cols=metric_resolution.revenue_cols,
        cost_month_year_cols=metric_resolution.cost_cols,
    )

    return IngestionResult(
        status="resolved",
        column_mapping=mapping,
        header_row_index=header_row_index,
        header_row_confidence=header_row_confidence,
    )


def apply_user_choice(
        result: IngestionResult,
        field: str,
        chosen_column: str,
) -> None:
    """
    Helper for the UI layer: once the user answers a clarification for
    `field`, call this to remove that clarification from the result.
    This does NOT re-run the pipeline -- it's a thin convenience for
    building the final ColumnMapping once all clarifications for a
    dataset have been answered in the UI layer, which is expected to
    accumulate answers and construct the ColumnMapping directly once
    every field is resolved (project_col, region_col,
    revenue_month_year_cols, cost_month_year_cols).
    """
    result.clarifications = [
        c for c in result.clarifications
        if c.field != field
    ]

    if not result.clarifications:
        result.status = "resolved"