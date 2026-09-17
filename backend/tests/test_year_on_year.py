"""
Tests for analyze_year_on_year -- the CORRECT 2-year comparison
(previous year X vs current year Y), 24 months total, not the
3-year/36-month version this used to incorrectly implement.

Reuses the same target C values as the other hand-computed cases
(100, 80, 60, 40, -10, -50 -> sumToReach=220) by holding year X's total
constant at 100 for every project (all in January) and varying year
Y's total, so the expected selection/sentence output is already
hand-verified.
"""

import pandas as pd
from analysis.year_on_year import analyze_year_on_year


def _build_case():
    year_y_targets = {"P1": 200, "P2": 180, "P3": 160, "P4": 140, "P5": 90, "P6": 50}
    rows = []
    for project, y_target in year_y_targets.items():
        row = {"Project Name": project}
        for m in range(1, 13):
            row[f"{m:02d}/2025"] = 100 if m == 1 else 0  # Year X total = 100
        for m in range(1, 13):
            row[f"{m:02d}/2026"] = y_target if m == 1 else 0  # Year Y total = target
        rows.append(row)
    return pd.DataFrame(rows)


def _quarters_for_year(year: int) -> dict[str, list[str]]:
    return {
        f"Q1 {year}": [f"{m:02d}/{year}" for m in (1, 2, 3)],
        f"Q2 {year}": [f"{m:02d}/{year}" for m in (4, 5, 6)],
        f"Q3 {year}": [f"{m:02d}/{year}" for m in (7, 8, 9)],
        f"Q4 {year}": [f"{m:02d}/{year}" for m in (10, 11, 12)],
    }


def test_two_year_comparison_matches_hand_computed_values():
    df = _build_case()
    year_x_months = [f"{m:02d}/2025" for m in range(1, 13)]
    year_y_months = [f"{m:02d}/2026" for m in range(1, 13)]

    result = analyze_year_on_year(
        df,
        project_col="Project Name",
        year_x_months=year_x_months,
        year_y_months=year_y_months,
        year_x_quarters=_quarters_for_year(2025),
        year_y_quarters=_quarters_for_year(2026),
        year_x_label="2025",
        year_y_label="2026",
    )

    assert result["sum_to_reach"] == 220

    view = result["comparison_view"]
    p1 = view[view["Project Name"] == "P1"].iloc[0]
    assert p1["2025"] == 100
    assert p1["2026"] == 200
    assert p1["A"] == 100
    assert p1["B"] == 200
    assert p1["C"] == 100
    # Quarter totals: all of year X's value sits in Q1.
    assert p1["Q1 2025"] == 100
    assert p1["Q2 2025"] == 0
    assert p1["Q1 2026"] == 200

    sentence = result["summary_sentence"]
    assert "net increase of 220" in sentence
    assert "P1, P2, P3, P4" in sentence
    assert "P6, P5" in sentence


def test_view_contains_24_months_plus_8_quarter_totals():
    df = _build_case()
    year_x_months = [f"{m:02d}/2025" for m in range(1, 13)]
    year_y_months = [f"{m:02d}/2026" for m in range(1, 13)]

    result = analyze_year_on_year(
        df,
        project_col="Project Name",
        year_x_months=year_x_months,
        year_y_months=year_y_months,
        year_x_quarters=_quarters_for_year(2025),
        year_y_quarters=_quarters_for_year(2026),
        year_x_label="2025",
        year_y_label="2026",
    )
    view_cols = set(result["comparison_view"].columns)
    for col in year_x_months + year_y_months:
        assert col in view_cols
    for q_label in list(_quarters_for_year(2025).keys()) + list(_quarters_for_year(2026).keys()):
        assert q_label in view_cols


def test_raises_when_year_y_not_complete():
    df = pd.DataFrame(
        {
            "Project Name": ["P1"],
            **{f"{m:02d}/2025": [100 if m == 1 else 0] for m in range(1, 13)},
            # 2026 (year Y) is missing entirely -- not yet complete
        }
    )
    try:
        analyze_year_on_year(
            df,
            project_col="Project Name",
            year_x_months=[f"{m:02d}/2025" for m in range(1, 13)],
            year_y_months=[f"{m:02d}/2026" for m in range(1, 13)],
            year_x_quarters=_quarters_for_year(2025),
            year_y_quarters=_quarters_for_year(2026),
            year_x_label="2025",
            year_y_label="2026",
        )
        assert False, "expected ValueError"
    except ValueError as e:
        assert "not yet complete" in str(e)


def test_raises_when_not_exactly_twelve_months():
    df = _build_case()
    try:
        analyze_year_on_year(
            df,
            project_col="Project Name",
            year_x_months=[f"{m:02d}/2025" for m in range(1, 6)],  # only 5 months
            year_y_months=[f"{m:02d}/2026" for m in range(1, 13)],
            year_x_quarters=_quarters_for_year(2025),
            year_y_quarters=_quarters_for_year(2026),
            year_x_label="2025",
            year_y_label="2026",
        )
        assert False, "expected ValueError"
    except ValueError:
        pass