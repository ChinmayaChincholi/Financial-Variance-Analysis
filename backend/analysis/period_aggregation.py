"""
Sums pre-resolved groups of month columns into period totals.

This module does NOT interpret column names in any way -- it takes a
mapping of {period_label: [month_cols]} that has ALREADY been decided
by the caller (the ingestion/NLP layer, or hand-specified in tests) and
simply sums, per project, whichever columns are listed under each
label. This is the only piece of "period aggregation" that belongs in
the analysis engine; the date-parsing that PRODUCES the mapping lives
in ingestion/period_grouping.py, kept deliberately separate.
"""

import pandas as pd


def aggregate_periods(
        df: pd.DataFrame, period_groups: dict[str, list[str]]
) -> pd.DataFrame:
    """
    Given a project-level DataFrame (one row per project, monthly
    columns) and a mapping of period label -> list of month columns,
    returns a new DataFrame with one summed column per period, in the
    order period_groups was given.

    Example: period_groups = {"Q1 2026": ["Jan 2026", "Feb 2026", "Mar 2026"]}
    produces a column "Q1 2026" = row-wise sum of those 3 month columns.
    """
    result = pd.DataFrame(index=df.index)
    for label, cols in period_groups.items():
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise ValueError(f"Columns for period '{label}' not found: {missing}")
        result[label] = df[cols].sum(axis=1)
    return result