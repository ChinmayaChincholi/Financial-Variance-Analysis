"""
Dispatch layer for the 4 views defined in the spec:
  - Unique Projects & Revenue/Cost
  - Analysis by Revenue/Cost (Month-on-Month / Quarter-on-Quarter / Year-on-Year)

Both Project-wise and Region-wise analysis call through here.

Note on Revenue vs Cost: the analysis math is identical either way --
"revenue" and "cost" are just two different sets of month_cols in the
client's dataset. This layer doesn't distinguish them.

Note on period_type inputs: M-o-M, Q-o-Q, and Y-o-Y each take
genuinely different arguments (see their own modules' docstrings) --
M-o-M takes a flat 3-month list; Q-o-Q takes two 3-month quarter
groups; Y-o-Y takes two 12-month year groups plus their quarter
breakdowns. Rather than force a false uniform shape, this dispatcher
forwards whatever period-specific kwargs the caller provides directly
to the matching analysis function, which validates its own arguments.
"""

from typing import Literal, Optional

import pandas as pd

from analysis.unique_projects import get_unique_projects
from analysis.month_on_month import analyze_month_on_month
from analysis.quarter_on_quarter import analyze_quarter_on_quarter
from analysis.year_on_year import analyze_year_on_year

PeriodType = Literal["MoM", "QoQ", "YoY"]

_PERIOD_DISPATCH = {
    "MoM": analyze_month_on_month,
    "QoQ": analyze_quarter_on_quarter,
    "YoY": analyze_year_on_year,
}


def unique_projects_view(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
) -> pd.DataFrame:
    """The 'View Unique Projects & Revenue/Cost' view."""
    return get_unique_projects(df, project_col, month_cols)


def analysis_by_period_view(
        df: pd.DataFrame,
        project_col: str,
        period_type: PeriodType,
        **period_kwargs,
) -> dict:
    """
    The 'Analysis by Revenue/Cost' view.

    period_kwargs are forwarded as-is to the matching analysis
    function:
      - MoM expects: month_cols=[...]  (exactly 3)
      - QoQ expects: quarter_a_months=[...], quarter_b_months=[...],
                      quarter_a_label=..., quarter_b_label=...
      - YoY expects: year_x_months=[...], year_y_months=[...],
                      year_x_quarters={...}, year_y_quarters={...},
                      year_x_label=..., year_y_label=...
    """
    if period_type not in _PERIOD_DISPATCH:
        raise ValueError(
            f"Unknown period_type '{period_type}', expected one of "
            f"{list(_PERIOD_DISPATCH.keys())}"
        )
    analysis_fn = _PERIOD_DISPATCH[period_type]
    return analysis_fn(df, project_col, **period_kwargs)


def run_analysis_view(
        df: pd.DataFrame,
        project_col: str,
        view: Literal["unique_projects", "analysis_by_period"],
        month_cols: Optional[list[str]] = None,
        period_type: Optional[PeriodType] = None,
        **period_kwargs,
):
    """
    Single entry point covering all 4 views. Routes to
    unique_projects_view or analysis_by_period_view based on `view`.
    """
    if view == "unique_projects":
        if month_cols is None:
            raise ValueError("month_cols is required for view='unique_projects'")
        return unique_projects_view(df, project_col, month_cols)
    elif view == "analysis_by_period":
        if period_type is None:
            raise ValueError(
                "period_type is required when view='analysis_by_period'"
            )
        # For MoM, month_cols is how the 3 months are supplied.
        if period_type == "MoM" and month_cols is not None:
            period_kwargs.setdefault("month_cols", month_cols)
        return analysis_by_period_view(df, project_col, period_type, **period_kwargs)
    else:
        raise ValueError(
            f"Unknown view '{view}', expected 'unique_projects' or "
            f"'analysis_by_period'"
        )