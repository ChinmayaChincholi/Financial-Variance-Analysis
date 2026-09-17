"""
Implements the 'Month-on-Month Analysis' logic from the spec.

Month-on-Month is the ONE analysis type that uses a 3-period chain:
given month1, month2, month3 (the most recent quarter's 3 months):
    A = month2 - month1  (created per spec, NOT used in analysis)
    B = month3 - month2  (created per spec, NOT used in analysis)
    C = month3 - month1  (the only variance actually used downstream)

Quarter-on-Quarter and Year-on-Year do NOT follow this pattern -- they
each compare exactly 2 periods directly (B - A), not a 3-period chain.
See quarter_on_quarter.py / year_on_year.py for their own formulas.
"""

import pandas as pd

from analysis.unique_projects import get_unique_projects
from analysis.variance_selection import finalize_variance_analysis


def analyze_month_on_month(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
) -> dict:
    """
    Full Month-on-Month analysis pipeline.

    Parameters
    ----------
    df : the raw dataset (already column-matched).
    project_col : the actual project-name column in df.
    month_cols : exactly 3 Month-Year columns, in chronological order,
                 e.g. ['Apr 2026', 'May 2026', 'Jun 2026'].

    Returns
    -------
    dict with 'comparison_view', 'sum_to_reach', 'summary_sentence'.
    comparison_view includes the 3 month columns plus A, B, C.
    """
    if len(month_cols) != 3:
        raise ValueError(
            f"Month-on-Month analysis requires exactly 3 month columns, "
            f"got {len(month_cols)}"
        )

    unique = get_unique_projects(df, project_col, month_cols)
    month1, month2, month3 = month_cols

    view = unique.copy()
    view["A"] = view[month2] - view[month1]
    view["B"] = view[month3] - view[month2]
    view["C"] = view[month3] - view[month1]

    return finalize_variance_analysis(view, project_col)