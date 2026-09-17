"""
Parses Month-Year column headers and groups them into Indian FISCAL
quarters/years (confirmed with the user): fiscal year runs April to
March, so:
    Fiscal Q1 = Apr, May, Jun
    Fiscal Q2 = Jul, Aug, Sep
    Fiscal Q3 = Oct, Nov, Dec
    Fiscal Q4 = Jan, Feb, Mar  (belongs to the fiscal year that STARTED
                                the previous April)

A fiscal year is labeled by the calendar year it STARTS in -- e.g.
"FY2025-26" runs April 2025 through March 2026. This convention was
verified directly against the doc's own worked example: "August 2026
to April 2025" only makes sense under fiscal quarters (calendar
quarters would give January 2025, not April 2025) -- see date_ranges.py
for that derivation.

This lives in `ingestion/`, NOT `analysis/`, because it requires
interpreting the MEANING of a column name's text. The analysis engine
never calls anything in this file directly -- it only receives the
already-resolved {period_label: [month_cols]} output as a plain
argument.
"""

from collections import defaultdict
from datetime import datetime

from dateutil import parser as dateutil_parser


def parse_month_year_column(column_name: str) -> tuple[int, int]:
    """
    Parses a Month-Year column header into (calendar_year, calendar_month).

    Uses dateutil's permissive parser, which already handles most
    real-world formats (Mar 2026, Mar-2026, March 2026, 03/2026,
    2026-03, 2026/03, etc.) without needing a hand-written format list.

    Raises ValueError if the column name can't be parsed as a date.
    """
    try:
        parsed = dateutil_parser.parse(column_name, default=datetime(2000, 1, 1))
        return parsed.year, parsed.month
    except (ValueError, OverflowError) as e:
        raise ValueError(
            f"Could not parse '{column_name}' as a Month-Year column"
        ) from e


def month_to_fiscal_quarter(calendar_year: int, calendar_month: int) -> tuple[int, int]:
    """
    Converts a calendar (year, month) into (fiscal_year, quarter_num).

    fiscal_year is the calendar year the fiscal year STARTED in, e.g.
    January 2026 -> fiscal_year=2025 (it belongs to FY2025-26, quarter 4),
    but April 2026 -> fiscal_year=2026 (start of FY2026-27, quarter 1).
    """
    if calendar_month in (4, 5, 6):
        return calendar_year, 1
    elif calendar_month in (7, 8, 9):
        return calendar_year, 2
    elif calendar_month in (10, 11, 12):
        return calendar_year, 3
    else:  # calendar_month in (1, 2, 3)
        return calendar_year - 1, 4


def format_fiscal_quarter_label(fiscal_year: int, quarter_num: int) -> str:
    """e.g. (2025, 1) -> 'Q1 FY2025-26'"""
    next_year_suffix = (fiscal_year + 1) % 100
    return f"Q{quarter_num} FY{fiscal_year}-{next_year_suffix:02d}"


def format_fiscal_year_label(fiscal_year: int) -> str:
    """e.g. 2025 -> 'FY2025-26'"""
    next_year_suffix = (fiscal_year + 1) % 100
    return f"FY{fiscal_year}-{next_year_suffix:02d}"


def group_months_into_fiscal_quarters_structured(
        month_cols: list[str],
) -> dict[tuple[int, int], list[str]]:
    """
    Groups Month-Year columns by (fiscal_year, quarter_num), sorted
    chronologically. This structured (integer-keyed) form is used
    internally for date comparisons (e.g. "has quarter Qb happened
    yet?") -- see date_ranges.py.
    """
    parsed = [(col, *parse_month_year_column(col)) for col in month_cols]

    groups: dict[tuple[int, int], list[str]] = defaultdict(list)
    for col, year, month in parsed:
        key = month_to_fiscal_quarter(year, month)
        groups[key].append(col)

    ordered_keys = sorted(groups.keys())
    return {key: groups[key] for key in ordered_keys}


def group_months_into_quarters(month_cols: list[str]) -> dict[str, list[str]]:
    """
    Public, string-labeled version -- this is what gets handed to the
    analysis layer (analysis/quarter_on_quarter.py never sees a raw
    (fiscal_year, quarter_num) tuple, only a plain label string).
    """
    structured = group_months_into_fiscal_quarters_structured(month_cols)
    return {
        format_fiscal_quarter_label(*key): cols for key, cols in structured.items()
    }


def group_months_into_fiscal_years_structured(
        month_cols: list[str],
) -> dict[int, list[str]]:
    """Groups Month-Year columns by fiscal_year, sorted chronologically."""
    parsed = [(col, *parse_month_year_column(col)) for col in month_cols]

    groups: dict[int, list[str]] = defaultdict(list)
    for col, year, month in parsed:
        fiscal_year, _ = month_to_fiscal_quarter(year, month)
        groups[fiscal_year].append(col)

    ordered_keys = sorted(groups.keys())
    return {key: groups[key] for key in ordered_keys}


def group_months_into_years(month_cols: list[str]) -> dict[str, list[str]]:
    """Public, string-labeled version, for the analysis layer."""
    structured = group_months_into_fiscal_years_structured(month_cols)
    return {format_fiscal_year_label(key): cols for key, cols in structured.items()}