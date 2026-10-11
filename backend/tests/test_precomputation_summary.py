from datetime import date

import pandas as pd

from analysis.quarter_on_quarter import analyze_quarter_on_quarter
from services.precomputation_service import (
    _analysis_result_to_dict,
    _build_summary,
    _driver_selection,
)


def _qoq_result():
    df = pd.DataFrame(
        {
            "Project": ["Alpha", "Kite", "Orion", "Nova", "Vega", "Delta"],
            "Apr 2026": [10, 5, 9, 2, 3, 4],
            "May 2026": [10, 5, 9, 2, 3, 4],
            "Jun 2026": [10, 5, 9, 2, 3, 4],
            "Jul 2026": [30, 15, 3, 3, 2, 4],
            "Aug 2026": [30, 15, 3, 3, 2, 4],
            "Sep 2026": [30, 15, 3, 3, 2, 4],
        }
    )
    result = analyze_quarter_on_quarter(
        df,
        "Project",
        ["Apr 2026", "May 2026", "Jun 2026"],
        ["Jul 2026", "Aug 2026", "Sep 2026"],
        "Q1 FY2026-27",
        "Q2 FY2026-27",
    )
    return df, result


def test_drivers_match_the_names_in_the_summary_sentence():
    _, result = _qoq_result()
    drivers = _driver_selection(result, "Project")

    assert drivers["top"][0] == "Alpha"
    assert drivers["bottom"][0] == "Orion"
    sentence = result["summary_sentence"]
    for name in drivers["top"] + drivers["bottom"]:
        assert name in sentence


def test_analysis_result_dict_keeps_sentence_and_adds_drivers():
    _, result = _qoq_result()
    payload = _analysis_result_to_dict(result, "Project")

    assert payload["summary_sentence"] == result["summary_sentence"]
    assert payload["sum_to_reach"] == float(result["sum_to_reach"])
    assert set(payload["drivers"]) == {"top", "bottom"}
    assert "C" in payload["columns"]


def test_summary_counts_projects_months_and_comparisons():
    df, _ = _qoq_result()
    months = [c for c in df.columns if c != "Project"]
    periods = {
        "revenue": {"mom": [{}], "qoq": [{}, {}], "yoy": []},
        "cost": {"mom": [], "qoq": [], "yoy": []},
    }

    summary = _build_summary(
        df=df,
        project_col="Project",
        revenue_cols=months,
        cost_cols=[],
        regions=["IN", "US"],
        periods=periods,
        as_of=date(2026, 10, 10),
    )

    assert summary["unique_projects"] == 6
    assert summary["row_count"] == 6
    assert summary["regions"] == ["IN", "US"]
    assert summary["first_month"] == "Apr 2026"
    assert summary["last_month"] == "Sep 2026"
    assert summary["month_count"] == 6
    assert summary["metrics"] == ["revenue"]
    assert summary["comparisons"] == {"mom": 1, "qoq": 2, "yoy": 0}