"""
Tests for date_ranges.py. test_matches_doc_own_worked_example is the
most important test here: it reproduces the doc's literal "August 2026
to April 2025" example directly, rather than a case I constructed
myself -- that's the strongest evidence this logic is correct.
"""

from datetime import date

from ingestion.date_ranges import (
    determine_current_fiscal_quarter,
    determine_unique_projects_range,
    get_valid_quarter_pairs,
    validate_quarter_pair_selection,
)


def test_matches_doc_own_worked_example():
    """
    The doc's literal example: 'Month-Year columns starting from the
    most recent month of the most recent quarter to the first quarter
    of the previous year. Example - August 2026 to April 2025.'

    Dataset spans April 2024 through August 2026 (more than needed);
    as_of = August 2026 should select exactly April 2025 -> August 2026.
    """
    month_cols = [f"{m:02d}/{y}" for y in [2024, 2025] for m in range(1, 13)] + [
        f"{m:02d}/2026" for m in range(1, 9)
    ]

    result = determine_unique_projects_range(month_cols, as_of=date(2026, 8, 15))

    assert result[0] == "04/2025"  # April 2025 -- matches doc exactly
    assert result[-1] == "08/2026"  # August 2026 -- matches doc exactly
    # Confirm nothing outside the range leaked in.
    assert "03/2025" not in result  # March 2025 would be too early
    assert "09/2026" not in result  # doesn't even exist in this dataset anyway


def test_range_is_ascending_chronological_order():
    month_cols = [f"{m:02d}/2025" for m in range(1, 13)]
    result = determine_unique_projects_range(month_cols, as_of=date(2025, 6, 1))
    # Ascending: earliest column first.
    parsed_months = [int(c.split("/")[0]) for c in result]
    assert parsed_months == sorted(parsed_months)


def test_ignores_future_columns_beyond_as_of():
    """A dataset might contain placeholder future-month columns; these
    shouldn't be treated as 'the most recent available data'."""
    month_cols = [f"{m:02d}/2025" for m in range(1, 13)] + ["01/2026", "02/2026"]
    result = determine_unique_projects_range(month_cols, as_of=date(2025, 8, 1))
    assert "01/2026" not in result
    assert "02/2026" not in result
    assert result[-1] == "08/2025"


def test_determine_current_fiscal_quarter():
    assert determine_current_fiscal_quarter(date(2026, 8, 15)) == (2026, 2)
    assert determine_current_fiscal_quarter(date(2026, 2, 1)) == (2025, 4)


def test_get_valid_quarter_pairs_excludes_future_quarters():
    """
    The doc's own scenario: current fiscal quarter is Q2 (e.g. today is
    August, fiscal_year=2026). Q2-Q3 should NOT be offered as valid
    (Q3 hasn't happened), but Q1-Q2 should be, since both exist and
    neither is in the future.
    """
    month_cols = [f"{m:02d}/2026" for m in range(4, 9)]  # Apr-Aug 2026 (Q1 and partial Q2)

    valid = get_valid_quarter_pairs(month_cols, fiscal_year=2026, as_of=date(2026, 8, 15))
    valid_pair_names = [v["pair"] for v in valid]

    assert "Q1-Q2" in valid_pair_names
    assert "Q2-Q3" not in valid_pair_names  # Q3 (Oct-Dec) hasn't happened
    assert "Q3-Q4" not in valid_pair_names


def test_validate_quarter_pair_selection_raises_not_reached():
    """Directly reproduces the doc's own example: current fiscal
    quarter is Q2, client selects Q2-Q3 -> 'Not Reached Quarter Q3'."""
    try:
        validate_quarter_pair_selection(
            pair="Q2-Q3", fiscal_year=2026, as_of=date(2026, 8, 15)
        )
        assert False, "expected ValueError"
    except ValueError as e:
        assert str(e) == "Not Reached Quarter Q3"


def test_validate_quarter_pair_selection_passes_for_valid_pair():
    # Should NOT raise -- Q1-Q2 has both quarters already happened.
    validate_quarter_pair_selection(pair="Q1-Q2", fiscal_year=2026, as_of=date(2026, 8, 15))


def test_validate_quarter_pair_selection_handles_q4_q1_wraparound():
    """Q4-Q1 spans into the NEXT fiscal year -- confirm this doesn't
    get miscompared against the current quarter incorrectly."""
    # If today is deep into fiscal Q1 of FY2027-28 (e.g. May 2027),
    # then Q4 FY2026-27 -> Q1 FY2027-28 should be a VALID, already-
    # happened pair.
    validate_quarter_pair_selection(pair="Q4-Q1", fiscal_year=2026, as_of=date(2027, 5, 1))

    # But if today is still in Q4 FY2026-27 (e.g. Feb 2027), Q1 of the
    # NEXT fiscal year hasn't happened yet.
    try:
        validate_quarter_pair_selection(pair="Q4-Q1", fiscal_year=2026, as_of=date(2027, 2, 1))
        assert False, "expected ValueError"
    except ValueError as e:
        assert str(e) == "Not Reached Quarter Q1"