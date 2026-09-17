"""
Implements the 'Year-on-Year Analysis' logic from the spec.

Compares exactly 2 specific years: X (previous year) and Y (current
year), valid only once all 4 quarters of Y are complete. The output
view contains:
    - 12 month columns for year X
    - 12 month columns for year Y
    - 4 quarter-total columns for year X
    - 4 quarter-total columns for year Y
    - Total(X), Total(Y)
    - C = Total(Y) - Total(X)

This module does not parse dates or decide which months/quarters
belong to X or Y -- those are already-resolved inputs from the
ingestion layer (see ingestion/period_grouping.py).
"""

import pandas as pd

from analysis.unique_projects import get_unique_projects
from analysis.period_aggregation import aggregate_periods
from analysis.variance_selection import finalize_variance_analysis


def analyze_year_on_year(
        df: pd.DataFrame,
        project_col: str,
        year_x_months: list[str],
        year_y_months: list[str],
        year_x_quarters: dict[str, list[str]],
        year_y_quarters: dict[str, list[str]],
        year_x_label: str = "Year X",
        year_y_label: str = "Year Y",
) -> dict:
    """
    Full Year-on-Year analysis pipeline.

    Parameters
    ----------
    df : the raw dataset (already column-matched).
    project_col : the actual project-name column in df.
    year_x_months : the 12 month columns making up the previous year (X).
    year_y_months : the 12 month columns making up the current year (Y).
    year_x_quarters : already-resolved {quarter_label: [3 months]}
                      mapping for year X, exactly 4 entries.
    year_y_quarters : same, for year Y, exactly 4 entries.
    year_x_label / year_y_label : display labels for the two yearly
                      total columns, e.g. "2025" / "2026".

    Returns
    -------
    dict with 'comparison_view' (12+12 months, 4+4 quarter totals,
    Total X, Total Y, C), 'sum_to_reach', 'summary_sentence'.

    Raises
    ------
    ValueError if year_x_months/year_y_months aren't exactly 12 months
    each, if the quarter mappings don't have exactly 4 entries each, or
    if year Y's months aren't fully present in the dataset (the spec's
    "all 4 quarters of year Y must be completed" requirement).
    """
    if len(year_x_months) != 12:
        raise ValueError(
            f"year_x_months must have exactly 12 months, got {len(year_x_months)}"
        )
    if len(year_y_months) != 12:
        raise ValueError(
            f"year_y_months must have exactly 12 months, got {len(year_y_months)}"
        )
    if len(year_x_quarters) != 4:
        raise ValueError(
            f"year_x_quarters must have exactly 4 entries, got {len(year_x_quarters)}"
        )
    if len(year_y_quarters) != 4:
        raise ValueError(
            f"year_y_quarters must have exactly 4 entries, got {len(year_y_quarters)}"
        )

    missing_y = [c for c in year_y_months if c not in df.columns]
    if missing_y:
        raise ValueError(
            f"Year {year_y_label} is not yet complete -- the following "
            f"months are missing from the dataset: {missing_y}. "
            f"Year-on-Year analysis requires all 4 quarters of the "
            f"current year to be completed."
        )

    all_months = year_x_months + year_y_months
    unique = get_unique_projects(df, project_col, all_months)

    view = unique.copy()

    x_quarter_totals = aggregate_periods(unique, year_x_quarters)
    y_quarter_totals = aggregate_periods(unique, year_y_quarters)
    view = pd.concat([view, x_quarter_totals, y_quarter_totals], axis=1)

    view[year_x_label] = view[year_x_months].sum(axis=1)
    view[year_y_label] = view[year_y_months].sum(axis=1)
    view["A"] = view[year_x_label]
    view["B"] = view[year_y_label]
    view["C"] = view["B"] - view["A"]

    return finalize_variance_analysis(view, project_col)