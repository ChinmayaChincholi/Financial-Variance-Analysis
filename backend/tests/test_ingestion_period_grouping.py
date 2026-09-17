"""
Tests for the ingestion-layer FISCAL date parsing/grouping logic
(confirmed with the user: Indian fiscal year, April-March).
"""

import pytest

from ingestion.period_grouping import (
    parse_month_year_column,
    month_to_fiscal_quarter,
    format_fiscal_quarter_label,
    format_fiscal_year_label,
    group_months_into_quarters,
    group_months_into_years,
)


@pytest.mark.parametrize(
    "column_name,expected_year,expected_month",
    [
        ("Mar 2026", 2026, 3),
        ("Mar-2026", 2026, 3),
        ("March 2026", 2026, 3),
        ("03/2026", 2026, 3),
        ("2026-03", 2026, 3),
        ("2026/03", 2026, 3),
        ("Jan 2025", 2025, 1),
        ("Dec-2024", 2024, 12),
    ],
)
def test_parses_varied_month_year_formats(column_name, expected_year, expected_month):
    year, month = parse_month_year_column(column_name)
    assert year == expected_year
    assert month == expected_month


def test_raises_on_unparseable_column():
    with pytest.raises(ValueError):
        parse_month_year_column("Not A Date")


@pytest.mark.parametrize(
    "calendar_year,calendar_month,expected_fiscal_year,expected_quarter",
    [
        (2025, 4, 2025, 1),   # April -> fiscal Q1 of the year it's in
        (2025, 5, 2025, 1),
        (2025, 6, 2025, 1),
        (2025, 7, 2025, 2),   # July -> fiscal Q2
        (2025, 9, 2025, 2),
        (2025, 10, 2025, 3),  # October -> fiscal Q3
        (2025, 12, 2025, 3),
        (2026, 1, 2025, 4),   # January -> fiscal Q4 of the PREVIOUS fiscal year
        (2026, 3, 2025, 4),
        (2026, 8, 2026, 2),   # the doc's own example: August 2026 -> fiscal Q2 of FY2026-27
    ],
)
def test_month_to_fiscal_quarter(
        calendar_year, calendar_month, expected_fiscal_year, expected_quarter
):
    fiscal_year, quarter = month_to_fiscal_quarter(calendar_year, calendar_month)
    assert fiscal_year == expected_fiscal_year
    assert quarter == expected_quarter


def test_fiscal_quarter_label_format():
    assert format_fiscal_quarter_label(2025, 1) == "Q1 FY2025-26"
    assert format_fiscal_quarter_label(2026, 2) == "Q2 FY2026-27"


def test_fiscal_year_label_format():
    assert format_fiscal_year_label(2025) == "FY2025-26"


def test_groups_months_into_fiscal_quarters_correctly():
    month_cols = [
        "Apr 2025", "May 2025", "Jun 2025",   # fiscal Q1 FY2025-26
        "Jul 2025", "Aug 2025", "Sep 2025",   # fiscal Q2 FY2025-26
        "Jan 2026", "Feb 2026", "Mar 2026",   # fiscal Q4 FY2025-26 (NOT a new fiscal year!)
    ]
    groups = group_months_into_quarters(month_cols)

    assert list(groups.keys()) == ["Q1 FY2025-26", "Q2 FY2025-26", "Q4 FY2025-26"]
    assert groups["Q1 FY2025-26"] == ["Apr 2025", "May 2025", "Jun 2025"]
    assert groups["Q4 FY2025-26"] == ["Jan 2026", "Feb 2026", "Mar 2026"]


def test_groups_months_into_fiscal_years_correctly():
    # Jan-Mar 2026 belongs to FY2025-26 (fiscal year STARTED April 2025),
    # NOT FY2026-27 -- this is the case a naive calendar-year grouping
    # would get wrong.
    month_cols = ["Apr 2025", "Dec 2025", "Jan 2026", "Mar 2026", "Apr 2026"]
    groups = group_months_into_years(month_cols)

    assert list(groups.keys()) == ["FY2025-26", "FY2026-27"]
    assert set(groups["FY2025-26"]) == {"Apr 2025", "Dec 2025", "Jan 2026", "Mar 2026"}
    assert groups["FY2026-27"] == ["Apr 2026"]