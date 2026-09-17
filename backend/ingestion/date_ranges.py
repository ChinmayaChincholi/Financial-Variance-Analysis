"""
Date-driven logic that runs AFTER column matching resolves which
columns are Month-Year columns, and BEFORE anything is handed to the
analysis layer. Implements two specific doc requirements:

  (a) The Unique Projects & Revenue/Cost view's column range: "from the
      most recent month of the most recent quarter to the first
      quarter of the previous year" (verified fiscal-year example:
      August 2026 -> April 2025).

  (b) Which Quarter-on-Quarter pairs (Q1-Q2, Q2-Q3, Q3-Q4, Q4-Q1) are
      actually selectable given today's date, and producing the exact
      "Not Reached Quarter Qb" rejection the doc specifies.

Both take the already-resolved list of Month-Year columns as a plain
argument -- neither this module nor anything upstream of it does NLP
column-type matching; that's a separate concern this module consumes
the output of.
"""

from datetime import date
from typing import Optional

from ingestion.period_grouping import (
    parse_month_year_column,
    month_to_fiscal_quarter,
    format_fiscal_quarter_label,
    group_months_into_fiscal_quarters_structured,
)

FISCAL_QUARTER_PAIRS = ["Q1-Q2", "Q2-Q3", "Q3-Q4", "Q4-Q1"]


def determine_current_fiscal_quarter(as_of: Optional[date] = None) -> tuple[int, int]:
    """Returns (fiscal_year, quarter_num) for the given date (default: today)."""
    if as_of is None:
        as_of = date.today()
    return month_to_fiscal_quarter(as_of.year, as_of.month)


def determine_unique_projects_range(
        month_cols: list[str],
        as_of: Optional[date] = None,
) -> list[str]:
    """
    Selects the subset of month_cols that should appear in the Unique
    Projects & Revenue/Cost view, per the doc: from the first month of
    the previous fiscal year's Q1 (i.e. April of the previous fiscal
    year) through the most recent month actually available in the
    dataset (at or before `as_of`).

    Returns the selected columns in ASCENDING chronological order
    (oldest first) -- matching every other view in this app (e.g.
    Month-on-Month's month1/month2/month3 order). The doc's "starting
    from X to Y" phrasing describes the RANGE's boundaries, not
    necessarily a display direction, and ascending order is the
    existing convention everywhere else in the codebase.

    Raises ValueError if no month column falls at or before `as_of`.
    """
    if as_of is None:
        as_of = date.today()

    parsed = [(col, *parse_month_year_column(col)) for col in month_cols]

    # Only consider columns at or before the reference date -- a
    # dataset might contain placeholder/future columns that shouldn't
    # be treated as "the most recent available data".
    candidates = [(col, y, m) for col, y, m in parsed if (y, m) <= (as_of.year, as_of.month)]
    if not candidates:
        raise ValueError(
            f"No month columns found at or before {as_of.isoformat()}"
        )

    latest_col, latest_y, latest_m = max(candidates, key=lambda t: (t[1], t[2]))
    latest_fiscal_year, _ = month_to_fiscal_quarter(latest_y, latest_m)
    previous_fiscal_year = latest_fiscal_year - 1

    range_start = (previous_fiscal_year, 4)  # April of previous fiscal year
    range_end = (latest_y, latest_m)

    selected = [col for col, y, m in parsed if range_start <= (y, m) <= range_end]
    selected.sort(key=lambda col: parse_month_year_column(col))
    return selected


def _pair_to_quarter_keys(
        pair: str, fiscal_year: int
) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Resolves a pair string like 'Q2-Q3' (for a given fiscal_year) into
    its two (fiscal_year, quarter_num) keys. Handles the Q4-Q1
    wraparound into the NEXT fiscal year.
    """
    qa_num, qb_num = (int(p.lstrip("Q")) for p in pair.split("-"))
    qa_key = (fiscal_year, qa_num)
    qb_fiscal_year = fiscal_year if qb_num > qa_num else fiscal_year + 1
    qb_key = (qb_fiscal_year, qb_num)
    return qa_key, qb_key


def get_valid_quarter_pairs(
        month_cols: list[str],
        fiscal_year: int,
        as_of: Optional[date] = None,
) -> list[dict]:
    """
    Given the full set of available Month-Year columns and a fiscal
    year the client is browsing, returns only the Qa-Qb pairs that are
    both (1) present in the dataset and (2) not in the future relative
    to `as_of` -- i.e. exactly the options that should be OFFERED to
    the client in the quarter-selection UI.

    Each result dict has: 'pair', 'quarter_a_label', 'quarter_b_label',
    'quarter_a_months', 'quarter_b_months'.
    """
    if as_of is None:
        as_of = date.today()

    current_key = determine_current_fiscal_quarter(as_of)
    quarter_groups = group_months_into_fiscal_quarters_structured(month_cols)

    valid_pairs = []
    for pair in FISCAL_QUARTER_PAIRS:
        qa_key, qb_key = _pair_to_quarter_keys(pair, fiscal_year)

        if qa_key not in quarter_groups or qb_key not in quarter_groups:
            continue  # data for this pair doesn't exist in the dataset
        if qb_key > current_key:
            continue  # Qb is in the future -- don't even offer it

        valid_pairs.append(
            {
                "pair": pair,
                "quarter_a_label": format_fiscal_quarter_label(*qa_key),
                "quarter_b_label": format_fiscal_quarter_label(*qb_key),
                "quarter_a_months": quarter_groups[qa_key],
                "quarter_b_months": quarter_groups[qb_key],
            }
        )

    return valid_pairs


def validate_quarter_pair_selection(
        pair: str,
        fiscal_year: int,
        as_of: Optional[date] = None,
) -> None:
    """
    Raises ValueError with the doc's exact 'Not Reached Quarter Qb'
    message if the client selected a quarter pair where Qb hasn't
    happened yet relative to `as_of`. Does nothing (returns None) if
    the selection is valid.
    """
    if as_of is None:
        as_of = date.today()

    current_key = determine_current_fiscal_quarter(as_of)
    _qa_key, qb_key = _pair_to_quarter_keys(pair, fiscal_year)

    if qb_key > current_key:
        _qb_fiscal_year, qb_num = qb_key
        raise ValueError(f"Not Reached Quarter Q{qb_num}")