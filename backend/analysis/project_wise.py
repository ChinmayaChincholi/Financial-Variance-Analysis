"""
Implements 'Project-wise Analysis' from the spec: the top-level entry
point exposing the 4 views over the FULL dataset (no region filtering).

This module is deliberately thin -- it's the public interface for
Project-wise Analysis; all real logic lives in views.py and below.
"""

from typing import Optional

import pandas as pd

from analysis.views import run_analysis_view, PeriodType


def run_project_wise_analysis(
        df: pd.DataFrame,
        project_col: str,
        view: str,
        month_cols: Optional[list[str]] = None,
        period_type: Optional[PeriodType] = None,
        **period_kwargs,
):
    """
    Project-wise Analysis entry point.

    Parameters
    ----------
    df : the raw dataset (already column-matched by the NLP service --
         this function receives only the actual column NAMES to use and
         has no awareness of how they were determined).
    project_col : the actual project-name column in df.
    view : 'unique_projects' or 'analysis_by_period'.
    month_cols : required for view='unique_projects'; also how M-o-M's
                 3 months are supplied when period_type='MoM'.
    period_type : required when view='analysis_by_period'; one of
                  'MoM', 'QoQ', 'YoY'.
    period_kwargs : period-specific arguments for Q-o-Q / Y-o-Y (see
                    views.analysis_by_period_view's docstring).

    Returns
    -------
    A DataFrame (for view='unique_projects') or a dict with
    'comparison_view' / 'sum_to_reach' / 'summary_sentence'
    (for view='analysis_by_period').
    """
    return run_analysis_view(
        df, project_col, view, month_cols=month_cols, period_type=period_type,
        **period_kwargs,
    )