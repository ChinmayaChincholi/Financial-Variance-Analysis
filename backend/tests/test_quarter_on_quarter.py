"""
Tests for analyze_quarter_on_quarter -- the CORRECT pairwise (2-quarter)
comparison per the actual doc spec, not a 3-period chain.

Reuses the same target C values as the Month-on-Month hand-computed
case (100, 80, 60, 40, -10, -50 -> sumToReach=220) by holding Qa
constant at 100 for every project and varying Qb, so the expected
selection/sentence output is already hand-verified.
"""

import pandas as pd
from analysis.quarter_on_quarter import analyze_quarter_on_quarter


def _build_case():
    qb_targets = {"P1": 200, "P2": 180, "P3": 160, "P4": 140, "P5": 90, "P6": 50}
    rows = []
    for project, qb_target in qb_targets.items():
        rows.append(
            {
                "Project Name": project,
                "Jan 2026": 100, "Feb 2026": 0, "Mar 2026": 0,       # Qa = 100
                "Apr 2026": qb_target, "May 2026": 0, "Jun 2026": 0,  # Qb = target
            }
        )
    return pd.DataFrame(rows)


def test_pairwise_quarter_comparison_matches_hand_computed_values():
    df = _build_case()

    result = analyze_quarter_on_quarter(
        df,
        project_col="Project Name",
        quarter_a_months=["Jan 2026", "Feb 2026", "Mar 2026"],
        quarter_b_months=["Apr 2026", "May 2026", "Jun 2026"],
        quarter_a_label="Q1 2026",
        quarter_b_label="Q2 2026",
    )

    assert result["sum_to_reach"] == 220

    view = result["comparison_view"]
    p1 = view[view["Project Name"] == "P1"].iloc[0]
    assert p1["Q1 2026"] == 100
    assert p1["Q2 2026"] == 200
    assert p1["A"] == 100
    assert p1["B"] == 200
    assert p1["C"] == 100

    sentence = result["summary_sentence"]
    assert "net increase of 220" in sentence
    assert "P1, P2, P3, P4" in sentence
    assert "P6, P5" in sentence


def test_view_contains_both_quarters_raw_months():
    df = _build_case()
    result = analyze_quarter_on_quarter(
        df,
        project_col="Project Name",
        quarter_a_months=["Jan 2026", "Feb 2026", "Mar 2026"],
        quarter_b_months=["Apr 2026", "May 2026", "Jun 2026"],
        quarter_a_label="Q1 2026",
        quarter_b_label="Q2 2026",
    )
    view_cols = set(result["comparison_view"].columns)
    for col in ["Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026", "May 2026", "Jun 2026"]:
        assert col in view_cols


def test_raises_not_reached_quarter_when_qb_missing():
    df = pd.DataFrame(
        {
            "Project Name": ["P1"],
            "Jan 2026": [100], "Feb 2026": [0], "Mar 2026": [0],
            # Apr/May/Jun 2026 (Q2) do not exist yet in this dataset
        }
    )
    try:
        analyze_quarter_on_quarter(
            df,
            project_col="Project Name",
            quarter_a_months=["Jan 2026", "Feb 2026", "Mar 2026"],
            quarter_b_months=["Apr 2026", "May 2026", "Jun 2026"],
            quarter_a_label="Q1 2026",
            quarter_b_label="Q2 2026",
        )
        assert False, "expected ValueError"
    except ValueError as e:
        assert "Not Reached Quarter" in str(e)


def test_raises_when_quarter_does_not_have_exactly_three_months():
    df = _build_case()
    try:
        analyze_quarter_on_quarter(
            df,
            project_col="Project Name",
            quarter_a_months=["Jan 2026", "Feb 2026"],  # only 2 months
            quarter_b_months=["Apr 2026", "May 2026", "Jun 2026"],
            quarter_a_label="Q1 2026",
            quarter_b_label="Q2 2026",
        )
        assert False, "expected ValueError"
    except ValueError:
        pass