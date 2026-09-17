"""
Implements the 'Quarter-on-Quarter Analysis' logic from the spec.

Unlike Month-on-Month, this is NOT a 3-period chain -- the client picks
exactly 2 specific, consecutive quarters to compare (Q1-Q2, Q2-Q3,
Q3-Q4, or Q4-Q1, spanning into the next year for the Q4-Q1 case), and
the analysis compares only that pair:
    A = total revenue/cost of quarter Qa (sum of its 3 months)
    B = total revenue/cost of quarter Qb (sum of its 3 months)
    C = B - A

This module does not decide WHICH quarter pair is valid to select given
today's date, or which months belong to a given quarter -- both are
ingestion/API-layer concerns (the client picks Qa/Qb from a UI, and the
months making up each quarter are resolved via
ingestion/period_grouping.py). This function receives the already-
resolved month lists for Qa and Qb directly.
"""

import pandas as pd

from analysis.unique_projects import get_unique_projects
from analysis.variance_selection import finalize_variance_analysis


def analyze_quarter_on_quarter(
        df: pd.DataFrame,
        project_col: str,
        quarter_a_months: list[str],
        quarter_b_months: list[str],
        quarter_a_label: str = "Quarter A",
        quarter_b_label: str = "Quarter B",
) -> dict:
    """
    Full Quarter-on-Quarter analysis pipeline for one selected pair of
    consecutive quarters.

    Parameters
    ----------
    df : the raw dataset (already column-matched).
    project_col : the actual project-name column in df.
    quarter_a_months : the 3 month columns making up the earlier
                       quarter (Qa), in chronological order.
    quarter_b_months : the 3 month columns making up the later quarter
                       (Qb), in chronological order.
    quarter_a_label / quarter_b_label : display labels for the two
                       totals columns in the output view, e.g.
                       "Q1 2026" / "Q2 2026".

    Returns
    -------
    dict with 'comparison_view' (Project Name + Qa's 3 months + Qb's 3
    months + A + B + C), 'sum_to_reach', 'summary_sentence'.

    Raises
    ------
    ValueError if either quarter isn't exactly 3 months, or if quarter_b's
    columns aren't present in the dataset at all -- the latter is
    treated as the spec's 'Not Reached Quarter Qb' case: the client
    selected a quarter that hasn't happened yet / isn't in the data.
    """
    if len(quarter_a_months) != 3:
        raise ValueError(
            f"quarter_a_months must have exactly 3 months, got {len(quarter_a_months)}"
        )
    if len(quarter_b_months) != 3:
        raise ValueError(
            f"quarter_b_months must have exactly 3 months, got {len(quarter_b_months)}"
        )

    missing_b = [c for c in quarter_b_months if c not in df.columns]
    if missing_b:
        raise ValueError(
            f"Not Reached Quarter {quarter_b_label} -- the following months "
            f"are not present in the dataset: {missing_b}"
        )

    all_months = quarter_a_months + quarter_b_months
    unique = get_unique_projects(df, project_col, all_months)

    view = unique.copy()
    view[quarter_a_label] = view[quarter_a_months].sum(axis=1)
    view[quarter_b_label] = view[quarter_b_months].sum(axis=1)
    view["A"] = view[quarter_a_label]
    view["B"] = view[quarter_b_label]
    view["C"] = view["B"] - view["A"]

    return finalize_variance_analysis(view, project_col)