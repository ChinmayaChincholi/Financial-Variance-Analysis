"""
Tests for run_project_wise_analysis -- confirms the dispatch layer
routes to the correct underlying function and returns identical results
to calling that function directly.
"""

import pandas as pd
from analysis.project_wise import run_project_wise_analysis
from analysis.unique_projects import get_unique_projects
from analysis.month_on_month import analyze_month_on_month


def _sample_df():
    return pd.DataFrame(
        {
            "Client Project": ["A", "B", "A"],
            "Apr 2026": [100, 100, 300],
            "May 2026": [200, 120, 200],
            "Jun 2026": [150, 160, 180],
        }
    )


def test_unique_projects_view_matches_direct_call():
    df = _sample_df()
    month_cols = ["Apr 2026", "May 2026", "Jun 2026"]

    via_dispatch = run_project_wise_analysis(
        df, project_col="Client Project", view="unique_projects", month_cols=month_cols
    )
    direct = get_unique_projects(df, "Client Project", month_cols)

    pd.testing.assert_frame_equal(via_dispatch, direct)


def test_analysis_by_period_mom_matches_direct_call():
    df = _sample_df()
    month_cols = ["Apr 2026", "May 2026", "Jun 2026"]

    via_dispatch = run_project_wise_analysis(
        df,
        project_col="Client Project",
        view="analysis_by_period",
        month_cols=month_cols,
        period_type="MoM",
    )
    direct = analyze_month_on_month(df, "Client Project", month_cols)

    assert via_dispatch["sum_to_reach"] == direct["sum_to_reach"]
    assert via_dispatch["summary_sentence"] == direct["summary_sentence"]


def test_raises_when_period_type_missing_for_analysis_by_period():
    df = _sample_df()
    try:
        run_project_wise_analysis(
            df,
            project_col="Client Project",
            view="analysis_by_period",
            month_cols=["Apr 2026", "May 2026", "Jun 2026"],
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_raises_on_unknown_view():
    df = _sample_df()
    try:
        run_project_wise_analysis(
            df,
            project_col="Client Project",
            view="not_a_real_view",
            month_cols=["Apr 2026", "May 2026", "Jun 2026"],
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_revenue_and_cost_use_same_dispatch_different_columns():
    """
    Confirms 'Revenue' vs 'Cost' isn't special-cased anywhere -- it's
    purely which month_cols the caller passes in.
    """
    df = pd.DataFrame(
        {
            "Client Project": ["A", "B"],
            "Revenue Apr 2026": [100, 200],
            "Cost Apr 2026": [40, 80],
        }
    )

    revenue_result = run_project_wise_analysis(
        df,
        project_col="Client Project",
        view="unique_projects",
        month_cols=["Revenue Apr 2026"],
    )
    cost_result = run_project_wise_analysis(
        df,
        project_col="Client Project",
        view="unique_projects",
        month_cols=["Cost Apr 2026"],
    )

    assert revenue_result["Revenue Apr 2026"].tolist() == [100, 200]
    assert cost_result["Cost Apr 2026"].tolist() == [40, 80]