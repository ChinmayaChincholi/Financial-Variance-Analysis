"""
Dataset precomputation service.

After ingestion has successfully identified the dataset structure,
this service computes all analysis views required by the frontend.

The frontend therefore does not need to ask the backend to perform
analysis when the user clicks an option.

Architecture:

    Dataset
       ↓
    Ingestion
       ↓
    PrecomputationService
       ↓
    Complete DatasetSession
       ↓
    React
"""

from typing import Any

import pandas as pd

from ingestion.schema import IngestionResult
from ingestion.period_grouping import (
    group_months_into_fiscal_quarters_structured,
    group_months_into_fiscal_years_structured,
)

from analysis.project_wise import run_project_wise_analysis
from analysis.region_wise import (
    get_available_regions,
    run_region_wise_analysis,
)

from models.session import DatasetSession


def _dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Convert a DataFrame into JSON-safe records.
    """

    result = df.copy()

    # Replace pandas NaN/NaT with None.
    result = result.where(pd.notna(result), None)

    return result.to_dict(orient="records")


def _analysis_result_to_dict(result: dict) -> dict:
    """
    Convert an analysis-engine result into a JSON-safe dictionary.
    """

    return {
        "comparison_view": _dataframe_to_records(
            result["comparison_view"]
        ),
        "sum_to_reach": result["sum_to_reach"],
        "summary_sentence": result["summary_sentence"],
    }


def _build_unique_view(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
) -> list[dict]:
    """
    Build the unique-project view.
    """

    result = run_project_wise_analysis(
        df=df,
        project_col=project_col,
        view="unique_projects",
        month_cols=month_cols,
    )

    return _dataframe_to_records(result)


def _build_mom_view(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
) -> dict:
    """
    Build Month-on-Month analysis.
    """

    result = run_project_wise_analysis(
        df=df,
        project_col=project_col,
        view="analysis_by_period",
        period_type="MoM",
        month_cols=month_cols,
    )

    return _analysis_result_to_dict(result)


def _build_qoq_view(
        df: pd.DataFrame,
        project_col: str,
        quarter_a_months: list[str],
        quarter_b_months: list[str],
        quarter_a_label: str,
        quarter_b_label: str,
) -> dict:
    """
    Build one Quarter-on-Quarter comparison.
    """

    result = run_project_wise_analysis(
        df=df,
        project_col=project_col,
        view="analysis_by_period",
        period_type="QoQ",
        quarter_a_months=quarter_a_months,
        quarter_b_months=quarter_b_months,
        quarter_a_label=quarter_a_label,
        quarter_b_label=quarter_b_label,
    )

    return _analysis_result_to_dict(result)


def _build_yoy_view(
        df: pd.DataFrame,
        project_col: str,
        year_x_months: list[str],
        year_y_months: list[str],
        year_x_quarters: dict[str, list[str]],
        year_y_quarters: dict[str, list[str]],
        year_x_label: str,
        year_y_label: str,
) -> dict:
    """
    Build one Year-on-Year comparison.
    """

    result = run_project_wise_analysis(
        df=df,
        project_col=project_col,
        view="analysis_by_period",
        period_type="YoY",
        year_x_months=year_x_months,
        year_y_months=year_y_months,
        year_x_quarters=year_x_quarters,
        year_y_quarters=year_y_quarters,
        year_x_label=year_x_label,
        year_y_label=year_y_label,
    )

    return _analysis_result_to_dict(result)


def _build_metric_analysis(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
) -> dict:
    """
    Precompute all analysis types for one metric.

    metric can be either Revenue or Cost.

    Returns:

        unique
        mom
        qoq
        yoy
    """

    result = {
        "unique": None,
        "mom": None,
        "qoq": {},
        "yoy": {},
    }

    if not month_cols:
        return result

    # ---------------------------------------------------------
    # UNIQUE
    # ---------------------------------------------------------

    result["unique"] = _build_unique_view(
        df,
        project_col,
        month_cols,
    )

    # ---------------------------------------------------------
    # PERIOD GROUPING
    # ---------------------------------------------------------

    quarter_groups = group_months_into_fiscal_quarters_structured(
        month_cols
    )

    year_groups = group_months_into_fiscal_years_structured(
        month_cols
    )

    # ---------------------------------------------------------
    # MOM
    #
    # The analysis engine requires exactly three months.
    # Use the most recent three available months.
    # ---------------------------------------------------------

    chronological_months = list(month_cols)

    if len(chronological_months) >= 3:
        latest_three = chronological_months[-3:]

        result["mom"] = _build_mom_view(
            df,
            project_col,
            latest_three,
        )

    # ---------------------------------------------------------
    # QOQ
    #
    # Precompute every valid consecutive quarter pair.
    # ---------------------------------------------------------

    quarter_items = list(quarter_groups.items())

    for index in range(len(quarter_items) - 1):
        quarter_a_label, quarter_a_months = quarter_items[index]
        quarter_b_label, quarter_b_months = quarter_items[index + 1]

        if (
                len(quarter_a_months) != 3
                or len(quarter_b_months) != 3
        ):
            continue

        key = f"{quarter_a_label}__{quarter_b_label}"

        try:
            result["qoq"][key] = _build_qoq_view(
                df=df,
                project_col=project_col,
                quarter_a_months=quarter_a_months,
                quarter_b_months=quarter_b_months,
                quarter_a_label=quarter_a_label,
                quarter_b_label=quarter_b_label,
            )
        except ValueError:
            # An incomplete quarter should not prevent the remaining
            # valid precomputations from being generated.
            continue

    # ---------------------------------------------------------
    # YOY
    #
    # Precompute every consecutive pair of complete fiscal years.
    # ---------------------------------------------------------

    year_items = list(year_groups.items())

    for index in range(len(year_items) - 1):
        year_x_label, year_x_months = year_items[index]
        year_y_label, year_y_months = year_items[index + 1]

        if (
                len(year_x_months) != 12
                or len(year_y_months) != 12
        ):
            continue

        year_x_quarters = {
            label: months
            for label, months in quarter_groups.items()
            if all(month in year_x_months for month in months)
        }

        year_y_quarters = {
            label: months
            for label, months in quarter_groups.items()
            if all(month in year_y_months for month in months)
        }

        if (
                len(year_x_quarters) != 4
                or len(year_y_quarters) != 4
        ):
            continue

        key = f"{year_x_label}__{year_y_label}"

        try:
            result["yoy"][key] = _build_yoy_view(
                df=df,
                project_col=project_col,
                year_x_months=year_x_months,
                year_y_months=year_y_months,
                year_x_quarters=year_x_quarters,
                year_y_quarters=year_y_quarters,
                year_x_label=year_x_label,
                year_y_label=year_y_label,
            )
        except ValueError:
            continue

    return result


def _build_project_wise(
        df: pd.DataFrame,
        project_col: str,
        revenue_cols: list[str],
        cost_cols: list[str],
) -> dict:

    return {
        "revenue": _build_metric_analysis(
            df,
            project_col,
            revenue_cols,
        ),
        "cost": _build_metric_analysis(
            df,
            project_col,
            cost_cols,
        ),
    }


def _build_region_wise(
        df: pd.DataFrame,
        project_col: str,
        region_col: str,
        revenue_cols: list[str],
        cost_cols: list[str],
) -> dict:

    regions = get_available_regions(
        df,
        region_col,
    )

    result = {}

    for region in regions:

        filtered = df[
            df[region_col] == region
            ]

        result[region] = {
            "revenue": _build_metric_analysis(
                filtered,
                project_col,
                revenue_cols,
            ),
            "cost": _build_metric_analysis(
                filtered,
                project_col,
                cost_cols,
            ),
        }

    return result


def precompute_dataset(
        file_path: str,
        sheet_name: str,
        ingestion_result: IngestionResult,
) -> DatasetSession:

    """
    Load the resolved dataset and precompute every frontend view.
    """

    mapping = ingestion_result.column_mapping

    if mapping is None:
        raise ValueError(
            "Cannot precompute dataset without a column mapping."
        )

    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=ingestion_result.header_row_index,
    )

    project_col = mapping.project_col
    region_col = mapping.region_col

    revenue_cols = mapping.revenue_month_year_cols
    cost_cols = mapping.cost_month_year_cols

    project_wise = _build_project_wise(
        df=df,
        project_col=project_col,
        revenue_cols=revenue_cols,
        cost_cols=cost_cols,
    )

    region_wise = {}

    regions = []

    if region_col is not None:
        regions = get_available_regions(
            df,
            region_col,
        )

        region_wise = _build_region_wise(
            df=df,
            project_col=project_col,
            region_col=region_col,
            revenue_cols=revenue_cols,
            cost_cols=cost_cols,
        )

    return DatasetSession(
        sheet_name=sheet_name,
        mapping=mapping.model_dump(),
        regions=regions,
        project_wise=project_wise,
        region_wise=region_wise,
    )