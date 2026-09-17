"""
Implements 'Region-wise Analysis' from the spec: the client picks a
region, then gets the same 4 views as Project-wise Analysis, but scoped
to only that region's rows.

Filters the dataset to the selected region, then delegates to the exact
same view dispatch logic Project-wise Analysis uses.
"""

from typing import Optional

import pandas as pd

from analysis.views import run_analysis_view, PeriodType


def get_available_regions(df: pd.DataFrame, region_col: str) -> list[str]:
    """
    Returns the sorted list of distinct region values in the dataset --
    used to populate the region-picker UI once the client chooses
    Region-wise Analysis.
    """
    if region_col not in df.columns:
        raise ValueError(f"region_col '{region_col}' not found in dataset")
    return sorted(df[region_col].dropna().unique().tolist())


def filter_by_region(
        df: pd.DataFrame, region_col: str, region_value: str
) -> pd.DataFrame:
    """Returns only the rows belonging to the selected region."""
    if region_col not in df.columns:
        raise ValueError(f"region_col '{region_col}' not found in dataset")

    filtered = df[df[region_col] == region_value]

    if filtered.empty:
        raise ValueError(
            f"No rows found for region '{region_value}' in column "
            f"'{region_col}'. Available regions: "
            f"{get_available_regions(df, region_col)}"
        )
    return filtered


def run_region_wise_analysis(
        df: pd.DataFrame,
        region_col: str,
        region_value: str,
        project_col: str,
        view: str,
        month_cols: Optional[list[str]] = None,
        period_type: Optional[PeriodType] = None,
        **period_kwargs,
):
    """
    Region-wise Analysis entry point. Same parameters as
    run_project_wise_analysis, plus region_col and region_value to
    select which region's rows to analyze.
    """
    filtered = filter_by_region(df, region_col, region_value)
    return run_analysis_view(
        filtered, project_col, view, month_cols=month_cols,
        period_type=period_type, **period_kwargs,
    )