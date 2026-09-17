"""
Implements the 'View Unique Projects & Revenue/Cost' logic from the spec:

- A project name can appear more than once in the raw dataset (different
  resources may have worked on the same project).
- We must take all distinct project names and SUM the revenue/cost for
  each Month-Year column across all rows sharing that project name.
- The output view contains only: Project Name + the requested Month-Year
  columns (in the order they were given).

This is also the single choke point every other analysis function
(Month-on-Month, Quarter-on-Quarter, Year-on-Year) routes through
first, so the data-quality checks here (per the doc's "Edge Cases to
handle" section) protect all four views at once.
"""

import pandas as pd


def _validate_no_missing_project_names(df: pd.DataFrame, project_col: str) -> None:
    """
    Raises a clear error if any row has a missing/blank project name.

    Without this check, pandas' groupby silently DROPS rows with a NaN
    group key -- meaning that revenue/cost would vanish from the
    analysis with no warning at all. Per the doc: "Missing values --
    Any of the essential columns missing any values" must be handled,
    not silently ignored.
    """
    missing_mask = df[project_col].isna()
    if missing_mask.any():
        count = int(missing_mask.sum())
        example_rows = df.index[missing_mask].tolist()[:5]
        raise ValueError(
            f"{count} row(s) have a missing value in the project column "
            f"'{project_col}' (e.g. row(s) {example_rows}). Every row must "
            f"have a project name before analysis can run."
        )


def _validate_numeric_columns(df: pd.DataFrame, month_cols: list[str]) -> None:
    """
    Raises a clear error if any Month-Year column contains a value that
    can't be treated as a number.

    Without this check, summing a column with a stray text value (e.g.
    "N/A" typed into a revenue cell) raises a raw, unfriendly pandas
    TypeError deep inside groupby().sum(). Per the doc: "Incorrect data
    in the dataset -- Alphabetical entries in numerical columns" must
    be handled, not leaked as an internal exception.
    """
    for col in month_cols:
        coerced = pd.to_numeric(df[col], errors="coerce")
        # A value that failed to coerce shows up as NaN in `coerced` but
        # was NOT already NaN in the original column -- that's a real
        # bad value, not a legitimately missing one.
        bad_mask = coerced.isna() & df[col].notna()
        if bad_mask.any():
            bad_values = df.loc[bad_mask, col].tolist()[:5]
            bad_rows = df.index[bad_mask].tolist()[:5]
            raise ValueError(
                f"Column '{col}' contains non-numeric value(s) that cannot "
                f"be used in revenue/cost analysis: {bad_values} "
                f"(row(s) {bad_rows}). Please correct these values before "
                f"re-uploading the dataset."
            )


def get_unique_projects(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
) -> pd.DataFrame:
    """
    Collapse a raw dataset down to one row per distinct project, summing
    revenue/cost across the given Month-Year columns.

    Parameters
    ----------
    df : the raw dataset (already column-matched, i.e. project_col and
         month_cols are the ACTUAL column names in df, not the generic
         "Project Name" / "Month-Year" labels from the spec).
    project_col : the column in df that holds the project name.
    month_cols : the Month-Year columns to include, in the order they
                 should appear in the output.

    Returns
    -------
    A DataFrame with columns [project_col] + month_cols, one row per
    distinct project, sorted by first appearance in the input.

    Raises
    ------
    ValueError if project_col or any month_cols are missing from df,
    if any row has a missing project name, or if any month column
    contains a non-numeric value.
    """
    if project_col not in df.columns:
        raise ValueError(f"project_col '{project_col}' not found in dataset")

    missing = [c for c in month_cols if c not in df.columns]
    if missing:
        raise ValueError(f"month_cols not found in dataset: {missing}")

    _validate_no_missing_project_names(df, project_col)
    _validate_numeric_columns(df, month_cols)

    grouped = (
        df.groupby(project_col, sort=False)[month_cols]
        .sum()
        .reset_index()
    )

    return grouped[[project_col] + month_cols]