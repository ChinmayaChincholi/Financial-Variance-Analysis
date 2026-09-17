"""
Tests for run_region_wise_analysis and its supporting functions -- the
key thing under test is that region filtering correctly isolates rows
BEFORE analysis runs, so a region's numbers never leak in data from
another region.
"""

import pandas as pd
from analysis.region_wise import (
    run_region_wise_analysis,
    get_available_regions,
    filter_by_region,
)


def _sample_df():
    return pd.DataFrame(
        {
            "Place": ["North", "North", "South", "South", "East"],
            "Project Name": ["A", "B", "A", "C", "D"],
            "Apr 2026": [100, 200, 500, 700, 900],
            "May 2026": [110, 210, 510, 710, 910],
            "Jun 2026": [120, 220, 520, 720, 920],
        }
    )


def test_get_available_regions_returns_sorted_distinct_values():
    df = _sample_df()
    assert get_available_regions(df, "Place") == ["East", "North", "South"]


def test_filter_by_region_isolates_correct_rows_only():
    df = _sample_df()
    filtered = filter_by_region(df, "Place", "North")

    assert len(filtered) == 2
    assert set(filtered["Project Name"]) == {"A", "B"}
    # Confirm no South/East data leaked in.
    assert 500 not in filtered["Apr 2026"].values
    assert 900 not in filtered["Apr 2026"].values


def test_filter_by_region_raises_on_unknown_region():
    df = _sample_df()
    try:
        filter_by_region(df, "Place", "West")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_region_wise_unique_projects_view_only_sees_its_region():
    df = _sample_df()
    month_cols = ["Apr 2026", "May 2026", "Jun 2026"]

    result = run_region_wise_analysis(
        df,
        region_col="Place",
        region_value="South",
        project_col="Project Name",
        view="unique_projects",
        month_cols=month_cols,
    )

    # South has projects A and C (500/510/520 and 700/710/720) -- North's
    # project A (100/110/120) must NOT be summed into South's project A.
    assert set(result["Project Name"]) == {"A", "C"}
    a_row = result[result["Project Name"] == "A"].iloc[0]
    assert a_row["Apr 2026"] == 500  # not 100+500=600


def test_region_wise_analysis_by_period_scoped_to_region():
    df = _sample_df()
    month_cols = ["Apr 2026", "May 2026", "Jun 2026"]

    result = run_region_wise_analysis(
        df,
        region_col="Place",
        region_value="North",
        project_col="Project Name",
        view="analysis_by_period",
        month_cols=month_cols,
        period_type="MoM",
    )

    # North only: Project A (100->120, C=20) and Project B (200->220, C=20)
    assert result["sum_to_reach"] == 40


def test_region_wise_quarter_on_quarter_scoped_to_region():
    """Confirms Region-wise Analysis works through Q-o-Q, not just M-o-M
    -- the doc requires all 4 views to work identically under Region-wise,
    for all 3 period types."""
    df = pd.DataFrame(
        {
            "Place": ["North", "North", "South", "South"],
            "Project Name": ["A", "B", "A", "C"],
            "Jan 2026": [100, 100, 500, 700],
            "Feb 2026": [0, 0, 0, 0],
            "Mar 2026": [0, 0, 0, 0],
            "Apr 2026": [150, 120, 550, 720],
            "May 2026": [0, 0, 0, 0],
            "Jun 2026": [0, 0, 0, 0],
        }
    )

    result = run_region_wise_analysis(
        df,
        region_col="Place",
        region_value="North",
        project_col="Project Name",
        view="analysis_by_period",
        period_type="QoQ",
        quarter_a_months=["Jan 2026", "Feb 2026", "Mar 2026"],
        quarter_b_months=["Apr 2026", "May 2026", "Jun 2026"],
        quarter_a_label="Q1 2026",
        quarter_b_label="Q2 2026",
    )

    # North only: A (100->150, C=50) + B (100->120, C=20) = 70
    assert result["sum_to_reach"] == 70
    assert set(result["comparison_view"]["Project Name"]) == {"A", "B"}


def test_region_wise_year_on_year_scoped_to_region():
    """Confirms Region-wise Analysis works through Y-o-Y as well."""
    df = pd.DataFrame(
        {
            "Place": ["North", "South"],
            "Project Name": ["A", "A"],
            **{f"{m:02d}/2025": [100 if m == 1 else 0, 500 if m == 1 else 0] for m in range(1, 13)},
            **{f"{m:02d}/2026": [150 if m == 1 else 0, 550 if m == 1 else 0] for m in range(1, 13)},
        }
    )
    quarters_2025 = {
        "Q1 2025": [f"{m:02d}/2025" for m in (1, 2, 3)],
        "Q2 2025": [f"{m:02d}/2025" for m in (4, 5, 6)],
        "Q3 2025": [f"{m:02d}/2025" for m in (7, 8, 9)],
        "Q4 2025": [f"{m:02d}/2025" for m in (10, 11, 12)],
    }
    quarters_2026 = {
        "Q1 2026": [f"{m:02d}/2026" for m in (1, 2, 3)],
        "Q2 2026": [f"{m:02d}/2026" for m in (4, 5, 6)],
        "Q3 2026": [f"{m:02d}/2026" for m in (7, 8, 9)],
        "Q4 2026": [f"{m:02d}/2026" for m in (10, 11, 12)],
    }

    result = run_region_wise_analysis(
        df,
        region_col="Place",
        region_value="North",
        project_col="Project Name",
        view="analysis_by_period",
        period_type="YoY",
        year_x_months=[f"{m:02d}/2025" for m in range(1, 13)],
        year_y_months=[f"{m:02d}/2026" for m in range(1, 13)],
        year_x_quarters=quarters_2025,
        year_y_quarters=quarters_2026,
        year_x_label="2025",
        year_y_label="2026",
    )

    # North only: A goes 100 -> 150, C = 50 (South's 500->550 must not leak in)
    assert result["sum_to_reach"] == 50