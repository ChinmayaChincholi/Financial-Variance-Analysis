"""
Tests for Excel export functionality.

Confirms the exported file is a real, readable .xlsx with the
correct headers and data by round-tripping it through pandas.
"""

import os
import tempfile

import pandas as pd

from export.excel_exporter import export_dataframe_to_excel
from analysis.unique_projects import get_unique_projects


def test_exports_and_round_trips_correctly():
    df = pd.DataFrame(
        {
            "Project Name": ["A", "B"],
            "Apr 2026": [400, 100],
            "May 2026": [400, 120],
            "Jun 2026": [330, 160],
        }
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(
            tmp_dir,
            "unique_projects.xlsx",
        )

        export_dataframe_to_excel(
            df,
            output_path,
        )

        assert os.path.exists(output_path)

        read_back = pd.read_excel(output_path)

        pd.testing.assert_frame_equal(
            read_back,
            df,
        )


def test_exports_the_actual_unique_projects_view():
    """
    End-to-end test:
    raw data -> get_unique_projects() -> Excel export -> read back.
    """

    raw = pd.DataFrame(
        {
            "Project Name": ["A", "B", "A"],
            "Apr 2026": [100, 100, 300],
            "May 2026": [200, 120, 200],
            "Jun 2026": [150, 160, 180],
        }
    )

    view = get_unique_projects(
        raw,
        project_col="Project Name",
        month_cols=[
            "Apr 2026",
            "May 2026",
            "Jun 2026",
        ],
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(
            tmp_dir,
            "export.xlsx",
        )

        export_dataframe_to_excel(
            view,
            output_path,
            sheet_name="Unique Projects",
        )

        read_back = pd.read_excel(
            output_path,
            sheet_name="Unique Projects",
        )

        pd.testing.assert_frame_equal(
            read_back,
            view,
        )