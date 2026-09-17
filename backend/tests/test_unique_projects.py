"""
Ground-truth test using the EXACT worked example from the project spec
(the 'View Unique Projects & Revenue' section):

Input:
    Project Name | Apr 2026 | May 2026 | Jun 2026
    A            | 100      | 200      | 150
    B            | 100      | 120      | 160
    A            | 300      | 200      | 180

Expected output after collapsing to distinct projects:
    Project Name | Apr 2026 | May 2026 | Jun 2026
    A            | 400      | 400      | 330
    B            | 100      | 120      | 160
"""

import pandas as pd
from analysis.unique_projects import get_unique_projects


def test_doc_worked_example():
    raw = pd.DataFrame(
        {
            "Project Name": ["A", "B", "A"],
            "Apr 2026": [100, 100, 300],
            "May 2026": [200, 120, 200],
            "Jun 2026": [150, 160, 180],
        }
    )

    result = get_unique_projects(
        raw,
        project_col="Project Name",
        month_cols=["Apr 2026", "May 2026", "Jun 2026"],
    )

    expected = pd.DataFrame(
        {
            "Project Name": ["A", "B"],
            "Apr 2026": [400, 100],
            "May 2026": [400, 120],
            "Jun 2026": [330, 160],
        }
    )

    pd.testing.assert_frame_equal(
        result.reset_index(drop=True),
        expected.reset_index(drop=True),
    )


def test_raises_on_missing_project_column():
    raw = pd.DataFrame({"Apr 2026": [100]})
    try:
        get_unique_projects(raw, project_col="Project Name", month_cols=["Apr 2026"])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_raises_on_missing_month_column():
    raw = pd.DataFrame({"Project Name": ["A"]})
    try:
        get_unique_projects(raw, project_col="Project Name", month_cols=["Apr 2026"])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_raises_clear_error_on_non_numeric_value():
    """Per the doc's 'Edge Cases to handle': alphabetical entries in
    numerical columns must produce a clear error, not a raw pandas
    TypeError leaking out of groupby().sum()."""
    raw = pd.DataFrame(
        {
            "Project Name": ["A", "A"],
            "Jan 2026": [100, "oops"],
        }
    )
    try:
        get_unique_projects(raw, project_col="Project Name", month_cols=["Jan 2026"])
        assert False, "expected ValueError"
    except ValueError as e:
        assert "non-numeric" in str(e)
        assert "Jan 2026" in str(e)


def test_raises_clear_error_on_missing_project_name():
    """Per the doc's 'Edge Cases to handle': missing values in an
    essential column must be caught, not silently dropped by
    groupby (which drops NaN group keys by default)."""
    raw = pd.DataFrame(
        {
            "Project Name": ["A", None, "B"],
            "Jan 2026": [100, 200, 300],
        }
    )
    try:
        get_unique_projects(raw, project_col="Project Name", month_cols=["Jan 2026"])
        assert False, "expected ValueError"
    except ValueError as e:
        assert "missing value" in str(e)
        assert "Project Name" in str(e)


def test_allows_missing_values_in_month_columns():
    """A missing (NaN) REVENUE value is legitimate -- e.g. a project
    genuinely had no activity that month -- and should sum as 0, not
    raise an error. Only non-numeric GARBAGE values should be rejected."""
    raw = pd.DataFrame(
        {
            "Project Name": ["A", "A"],
            "Jan 2026": [100, None],
        }
    )
    result = get_unique_projects(raw, project_col="Project Name", month_cols=["Jan 2026"])
    assert result.loc[result["Project Name"] == "A", "Jan 2026"].values[0] == 100


def test_scales_to_many_rows_and_columns_with_arbitrary_names():
    """
    Confirms the function is NOT hardcoded to the doc's 3-row example:
    - 500 rows instead of 3
    - 50 distinct projects instead of 2
    - 24 Month-Year columns instead of 3
    - a project column named something other than "Project Name"
    """
    import numpy as np

    rng = np.random.default_rng(42)
    n_rows = 500
    projects = [f"Project-{i}" for i in range(50)]
    month_cols = [
        f"{m}-{y}"
        for y in [2024, 2025]
        for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ]

    raw = pd.DataFrame({"Client Project": rng.choice(projects, n_rows)})
    for col in month_cols:
        raw[col] = rng.integers(50, 5000, n_rows)

    result = get_unique_projects(raw, project_col="Client Project", month_cols=month_cols)

    # Every distinct project collapses to exactly one row.
    assert len(result) == raw["Client Project"].nunique()
    assert set(result["Client Project"]) == set(projects)

    # Spot-check: the sum for one project/column matches a manual sum.
    sample_project = projects[0]
    manual_sum = raw.loc[raw["Client Project"] == sample_project, month_cols[0]].sum()
    function_sum = result.loc[
        result["Client Project"] == sample_project, month_cols[0]
    ].values[0]
    assert manual_sum == function_sum