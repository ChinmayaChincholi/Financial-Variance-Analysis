import math

import pandas as pd

from services.currency_detection import (
    _text_to_number,
    coerce_text_amounts,
    detect_currency,
)


def _frame(**columns):
    return pd.DataFrame(columns)


def test_plain_numbers_and_plain_headers_assume_dollars():
    df = _frame(**{"Jan-26": [1, 2], "Feb-26": [3.5, 4]})
    currency = detect_currency(df, ["Jan-26", "Feb-26"])

    assert currency["code"] == "USD"
    assert currency["symbol"] == "$"
    assert currency["detected"] is False
    assert currency["mixed"] is False
    assert currency["source"] == "assumed"


def test_currency_symbol_in_headers_is_detected():
    df = _frame(**{"Jan-26 (₹)": [1, 2], "Feb-26 (₹)": [3, 4]})
    currency = detect_currency(df, list(df.columns))

    assert currency["code"] == "INR"
    assert currency["symbol"] == "₹"
    assert currency["detected"] is True
    assert currency["source"] == "headers"


def test_currency_code_in_headers_is_detected():
    df = _frame(**{"Jan-26 EUR": [1], "Feb-26 EUR": [2]})
    currency = detect_currency(df, list(df.columns))
    assert currency["code"] == "EUR"
    assert currency["symbol"] == "€"


def test_currency_in_text_values_is_detected():
    df = _frame(**{"Jan-26": ["$1,200.50", "$30"], "Feb-26": ["$5", None]})
    currency = detect_currency(df, list(df.columns))

    assert currency["code"] == "USD"
    assert currency["detected"] is True
    assert currency["source"] == "values"


def test_headers_and_values_agreeing_reports_both():
    df = _frame(**{"Jan-26 (£)": ["£10", "£20"]})
    currency = detect_currency(df, list(df.columns))
    assert currency["code"] == "GBP"
    assert currency["source"] == "both"


def test_conflicting_currencies_are_flagged_as_mixed_without_a_symbol():
    df = _frame(**{"Jan-26 (USD)": [1], "Feb-26 (INR)": [2]})
    currency = detect_currency(df, list(df.columns))

    assert currency["mixed"] is True
    assert currency["symbol"] == ""
    assert currency["code"] is None
    assert currency["found"] == ["INR", "USD"]


def test_only_month_columns_are_inspected():
    df = _frame(**{"Jan-26": [1], "Notes": ["pay in €"], "Revenue ₹": [5]})
    currency = detect_currency(df, ["Jan-26"])
    assert currency["detected"] is False
    assert currency["code"] == "USD"


def test_unknown_three_letter_code_does_not_trigger_detection():
    df = _frame(**{"Jan-26 ABC": [1]})
    assert detect_currency(df, list(df.columns))["detected"] is False


def test_text_amount_parsing():
    assert _text_to_number("$1,200.50") == 1200.50
    assert _text_to_number("(₹ 3,400)") == -3400
    assert _text_to_number("EUR 99") == 99
    assert _text_to_number("-45.5") == -45.5
    assert _text_to_number("1,23,456.78") == 123456.78
    assert _text_to_number("1.234,56 €") == 1234.56
    assert _text_to_number("12,5") == 12.5
    assert _text_to_number("1,200") == 1200
    assert _text_to_number(7) == 7.0
    assert math.isnan(_text_to_number(""))
    assert math.isnan(_text_to_number("n/a"))
    assert math.isnan(_text_to_number(None))


def test_coerce_converts_text_columns_without_touching_the_original():
    df = _frame(
        Project=["A", "B"],
        **{"Jan-26": ["$1,000.00", "(500)"], "Feb-26": [1.5, 2.5]},
    )
    result = coerce_text_amounts(df, ["Jan-26", "Feb-26"])

    assert list(result["Jan-26"]) == [1000.0, -500.0]
    assert result["Jan-26"].dtype == "float64"
    assert list(result["Feb-26"]) == [1.5, 2.5]
    assert df["Jan-26"].iloc[0] == "$1,000.00"  # input untouched


def test_coerce_returns_same_frame_when_everything_is_numeric():
    df = _frame(Project=["A"], **{"Jan-26": [1.0]})
    assert coerce_text_amounts(df, ["Jan-26"]) is df