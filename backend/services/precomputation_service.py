"""
Dataset precomputation service.

Once ingestion resolves the dataset structure, this service computes
EVERY view required by the frontend.

The frontend never asks the backend to perform analysis after this
point. It only reads the DatasetSession.
"""

from datetime import date
from typing import Any, Callable

import pandas as pd

from analysis.project_wise import run_project_wise_analysis
from analysis.region_wise import get_available_regions
from ingestion.date_ranges import determine_unique_projects_range
from ingestion.excel_io import read_sheet
from ingestion.period_grouping import (
    format_fiscal_quarter_label,
    format_fiscal_year_label,
    group_months_into_fiscal_quarters_structured,
    group_months_into_fiscal_years_structured,
    parse_month_year_column,
)
from ingestion.schema import IngestionResult
from models.session import DatasetSession

def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass

    return value

def _dataframe_to_records(
        df: pd.DataFrame,
) -> list[dict[str, Any]]:
    records = df.to_dict(
        orient="records"
    )

    return [
        {
            str(key): _json_safe_value(value)
            for key, value in record.items()
        }
        for record in records
    ]

def _analysis_result_to_dict(
        result: dict,
) -> dict[str, Any]:
    comparison_view = result[
        "comparison_view"
    ]

    return {
        "rows": _dataframe_to_records(
            comparison_view
        ),
        "columns": [
            str(column)
            for column in comparison_view.columns
        ],
        "sum_to_reach": float(
            result["sum_to_reach"]
        ),
        "summary_sentence": str(
            result["summary_sentence"]
        ),
    }

def _unique_result_to_dict(
        df: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "rows": _dataframe_to_records(df),
        "columns": [
            str(column)
            for column in df.columns
        ],
    }

def _chronological_columns(
        month_cols: list[str],
) -> list[str]:
    return sorted(
        month_cols,
        key=parse_month_year_column,
    )

def _available_months(
        month_cols: list[str],
        as_of: date,
) -> list[str]:
    result: list[str] = []

    for column in _chronological_columns(
            month_cols
    ):
        year, month = parse_month_year_column(
            column
        )

        if (year, month) <= (
                as_of.year,
                as_of.month,
        ):
            result.append(column)

    return result

def _complete_quarters(
        month_cols: list[str],
        as_of: date,
) -> dict[tuple[int, int], list[str]]:
    structured = (
        group_months_into_fiscal_quarters_structured(
            month_cols
        )
    )

    result: dict[
        tuple[int, int],
        list[str],
    ] = {}

    for key, columns in structured.items():
        if len(columns) != 3:
            continue

        all_available = True

        for column in columns:
            year, month = parse_month_year_column(
                column
            )

            if (year, month) > (
                    as_of.year,
                    as_of.month,
            ):
                all_available = False
                break

        if all_available:
            result[key] = columns

    return result

def _next_quarter_key(
        fiscal_year: int,
        quarter: int,
) -> tuple[int, int]:
    if quarter == 4:
        return fiscal_year + 1, 1

    return fiscal_year, quarter + 1

def _complete_years(
        month_cols: list[str],
        as_of: date,
) -> dict[int, list[str]]:
    structured = (
        group_months_into_fiscal_years_structured(
            month_cols
        )
    )

    result: dict[int, list[str]] = {}

    for fiscal_year, columns in structured.items():
        if len(columns) != 12:
            continue

        if all(
                parse_month_year_column(column)
                <= (
                        as_of.year,
                        as_of.month,
                )
                for column in columns
        ):
            result[fiscal_year] = columns

    return result

def _build_mom_option(
        months: list[str],
) -> dict[str, Any]:
    first, second, third = months

    option_id = (
        f"{first}__{second}__{third}"
    )

    return {
        "id": option_id,
        "label": f"{first} → {third}",
        "start_period": first,
        "end_period": third,
    }

def _build_qoq_option(
        qa_key: tuple[int, int],
        qb_key: tuple[int, int],
) -> dict[str, Any]:
    qa_label = format_fiscal_quarter_label(
        *qa_key
    )

    qb_label = format_fiscal_quarter_label(
        *qb_key
    )

    return {
        "id": (
            f"{qa_label}__{qb_label}"
        ),
        "label": (
            f"{qa_label} → {qb_label}"
        ),
        "start_period": qa_label,
        "end_period": qb_label,
    }

def _build_yoy_option(
        year_x: int,
        year_y: int,
) -> dict[str, Any]:
    x_label = format_fiscal_year_label(
        year_x
    )

    y_label = format_fiscal_year_label(
        year_y
    )

    return {
        "id": (
            f"{x_label}__{y_label}"
        ),
        "label": (
            f"{x_label} → {y_label}"
        ),
        "start_period": x_label,
        "end_period": y_label,
    }

def _build_period_metadata(
        month_cols: list[str],
        as_of: date,
) -> dict[str, list[dict[str, Any]]]:
    available = _available_months(
        month_cols,
        as_of,
    )

    mom: list[dict[str, Any]] = []

    if len(available) >= 3:
        mom.append(
            _build_mom_option(
                available[-3:]
            )
        )

    complete_quarters = _complete_quarters(
        month_cols,
        as_of,
    )

    qoq: list[dict[str, Any]] = []

    for qa_key in sorted(
            complete_quarters.keys()
    ):
        qb_key = _next_quarter_key(
            *qa_key
        )

        if qb_key not in complete_quarters:
            continue

        qoq.append(
            _build_qoq_option(
                qa_key,
                qb_key,
            )
        )

    complete_years = _complete_years(
        month_cols,
        as_of,
    )

    yoy: list[dict[str, Any]] = []

    for year_x in sorted(
            complete_years.keys()
    ):
        year_y = year_x + 1

        if year_y not in complete_years:
            continue

        yoy.append(
            _build_yoy_option(
                year_x,
                year_y,
            )
        )

    return {
        "mom": mom,
        "qoq": qoq,
        "yoy": yoy,
    }

def _build_unique_view(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
        as_of: date,
) -> dict[str, Any] | None:
    available = _available_months(
        month_cols,
        as_of,
    )

    if not available:
        return None

    selected = determine_unique_projects_range(
        available,
        as_of=as_of,
    )

    if not selected:
        return None

    result = run_project_wise_analysis(
        df=df,
        project_col=project_col,
        view="unique_projects",
        month_cols=selected,
    )

    return _unique_result_to_dict(result)

def _build_mom_views(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
        as_of: date,
) -> dict[str, dict[str, Any]]:
    available = _available_months(
        month_cols,
        as_of,
    )

    if len(available) < 3:
        return {}

    months = available[-3:]

    result = run_project_wise_analysis(
        df=df,
        project_col=project_col,
        view="analysis_by_period",
        period_type="MoM",
        month_cols=months,
    )

    option = _build_mom_option(
        months
    )

    return {
        option["id"]: _analysis_result_to_dict(
            result
        )
    }

def _build_qoq_views(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
        as_of: date,
) -> dict[str, dict[str, Any]]:
    quarter_groups = _complete_quarters(
        month_cols,
        as_of,
    )

    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for qa_key in sorted(
            quarter_groups.keys()
    ):
        qb_key = _next_quarter_key(
            *qa_key
        )

        if qb_key not in quarter_groups:
            continue

        qa_months = quarter_groups[
            qa_key
        ]

        qb_months = quarter_groups[
            qb_key
        ]

        qa_label = (
            format_fiscal_quarter_label(
                *qa_key
            )
        )

        qb_label = (
            format_fiscal_quarter_label(
                *qb_key
            )
        )

        analysis = run_project_wise_analysis(
            df=df,
            project_col=project_col,
            view="analysis_by_period",
            period_type="QoQ",
            quarter_a_months=qa_months,
            quarter_b_months=qb_months,
            quarter_a_label=qa_label,
            quarter_b_label=qb_label,
        )

        option = _build_qoq_option(
            qa_key,
            qb_key,
        )

        result[
            option["id"]
        ] = _analysis_result_to_dict(
            analysis
        )

    return result

def _build_yoy_views(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
        as_of: date,
) -> dict[str, dict[str, Any]]:
    year_groups = _complete_years(
        month_cols,
        as_of,
    )

    quarter_groups = _complete_quarters(
        month_cols,
        as_of,
    )

    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for year_x in sorted(
            year_groups.keys()
    ):
        year_y = year_x + 1

        if year_y not in year_groups:
            continue

        year_x_months = year_groups[
            year_x
        ]

        year_y_months = year_groups[
            year_y
        ]

        year_x_quarters = {
            format_fiscal_quarter_label(
                *key
            ): columns
            for key, columns
            in quarter_groups.items()
            if key[0] == year_x
               and all(
                month in year_x_months
                for month in columns
            )
        }

        year_y_quarters = {
            format_fiscal_quarter_label(
                *key
            ): columns
            for key, columns
            in quarter_groups.items()
            if key[0] == year_y
               and all(
                month in year_y_months
                for month in columns
            )
        }

        if (
                len(year_x_quarters) != 4
                or len(year_y_quarters) != 4
        ):
            continue

        year_x_label = (
            format_fiscal_year_label(
                year_x
            )
        )

        year_y_label = (
            format_fiscal_year_label(
                year_y
            )
        )

        analysis = run_project_wise_analysis(
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

        option = _build_yoy_option(
            year_x,
            year_y,
        )

        result[
            option["id"]
        ] = _analysis_result_to_dict(
            analysis
        )

    return result

def _build_metric_analysis(
        df: pd.DataFrame,
        project_col: str,
        month_cols: list[str],
        as_of: date,
) -> dict[str, Any]:
    if not month_cols:
        return {
            "unique": None,
            "mom": {},
            "qoq": {},
            "yoy": {},
        }

    return {
        "unique": _build_unique_view(
            df,
            project_col,
            month_cols,
            as_of,
        ),
        "mom": _build_mom_views(
            df,
            project_col,
            month_cols,
            as_of,
        ),
        "qoq": _build_qoq_views(
            df,
            project_col,
            month_cols,
            as_of,
        ),
        "yoy": _build_yoy_views(
            df,
            project_col,
            month_cols,
            as_of,
        ),
    }

def _build_project_wise(
        df: pd.DataFrame,
        project_col: str,
        revenue_cols: list[str],
        cost_cols: list[str],
        as_of: date,
        progress_callback: Callable[
                               [str],
                               None,
                           ] | None = None,
) -> dict[str, Any]:
    if progress_callback is not None:
        progress_callback(
            "Computing project-wise analysis"
        )

    return {
        "revenue": _build_metric_analysis(
            df,
            project_col,
            revenue_cols,
            as_of,
        ),
        "cost": _build_metric_analysis(
            df,
            project_col,
            cost_cols,
            as_of,
        ),
    }

def _build_region_wise(
        df: pd.DataFrame,
        project_col: str,
        region_col: str,
        revenue_cols: list[str],
        cost_cols: list[str],
        as_of: date,
        progress_callback: Callable[
                               [str],
                               None,
                           ] | None = None,
) -> dict[str, Any]:
    if progress_callback is not None:
        progress_callback(
            "Computing region-wise analysis"
        )

    regions = [
        str(region)
        for region in get_available_regions(
            df,
            region_col,
        )
    ]

    result: dict[str, Any] = {}

    for region in regions:
        filtered = df[
            df[region_col].astype(str)
            == region
            ]

        result[region] = {
            "revenue": _build_metric_analysis(
                filtered,
                project_col,
                revenue_cols,
                as_of,
            ),
            "cost": _build_metric_analysis(
                filtered,
                project_col,
                cost_cols,
                as_of,
            ),
        }

    return result

def precompute_dataset(
        file_path: str,
        sheet_name: str,
        ingestion_result: IngestionResult,
        filename: str,
        progress_callback: Callable[
                               [str],
                               None,
                           ] | None = None,
        dataframe: pd.DataFrame | None = None,
) -> DatasetSession:
    """
    Load the resolved dataset and compute the entire session.

    If `dataframe` is supplied (already parsed during ingestion with
    the same header row) it is reused; otherwise the workbook is read.

    progress_callback is called only at real stage boundaries.
    It does not report fabricated percentage progress.
    """

    mapping = ingestion_result.column_mapping

    if mapping is None:
        raise ValueError(
            "Cannot precompute dataset without "
            "a resolved column mapping."
        )

    header_row = (
        ingestion_result.header_row_index
        if ingestion_result.header_row_index
           is not None
        else 0
    )

    if dataframe is not None:
        df = dataframe
    else:
        df = read_sheet(
            file_path,
            sheet_name,
            header=header_row,
        )

    as_of = date.today()

    periods = {
        "revenue": _build_period_metadata(
            mapping.revenue_month_year_cols,
            as_of,
        ),
        "cost": _build_period_metadata(
            mapping.cost_month_year_cols,
            as_of,
        ),
    }

    project_wise = _build_project_wise(
        df=df,
        project_col=mapping.project_col,
        revenue_cols=(
            mapping.revenue_month_year_cols
        ),
        cost_cols=(
            mapping.cost_month_year_cols
        ),
        as_of=as_of,
        progress_callback=progress_callback,
    )

    regions: list[str] = []
    region_wise: dict[str, Any] = {}

    if mapping.region_col is not None:
        regions = [
            str(region)
            for region in get_available_regions(
                df,
                mapping.region_col,
            )
        ]

        region_wise = _build_region_wise(
            df=df,
            project_col=mapping.project_col,
            region_col=mapping.region_col,
            revenue_cols=(
                mapping.revenue_month_year_cols
            ),
            cost_cols=(
                mapping.cost_month_year_cols
            ),
            as_of=as_of,
            progress_callback=progress_callback,
        )
    elif progress_callback is not None:
        progress_callback(
            "Computing region-wise analysis"
        )

    return DatasetSession(
        filename=filename,
        sheet_name=sheet_name,
        row_count=len(df),
        column_count=len(df.columns),
        mapping=mapping.model_dump(),
        regions=regions,
        periods=periods,
        project_wise=project_wise,
        region_wise=region_wise,
    )