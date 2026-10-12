"""
Currency detection and text-amount cleanup for month-year columns.

Only the month-year columns are inspected:
- their HEADERS (e.g. "Jan-26 (USD)", "€ Feb-26")
- their VALUES, when a column holds text instead of numbers
  (e.g. "$1,200.50", "(₹ 3,400)", "EUR 99")

Rules
- exactly one currency found  -> that currency
- nothing found               -> US dollars (assumed)
- more than one currency found -> "mixed": amounts are shown without a
  symbol and are never converted

Text values are also converted to real numbers so analysis can run on them.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import numpy as np
import pandas as pd

# Longest tokens first so "HK$" wins over "$".
_SYMBOL_TO_CODE: dict[str, str] = {
    "US$": "USD",
    "HK$": "HKD",
    "NZ$": "NZD",
    "R$": "BRL",
    "A$": "AUD",
    "C$": "CAD",
    "S$": "SGD",
    "$": "USD",
    "₹": "INR",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₩": "KRW",
    "₽": "RUB",
    "₺": "TRY",
    "฿": "THB",
    "₫": "VND",
    "₪": "ILS",
    "₦": "NGN",
    "₱": "PHP",
}

_CODES: tuple[str, ...] = (
    "USD", "INR", "EUR", "GBP", "JPY", "CNY", "RMB", "AUD", "CAD", "CHF",
    "SGD", "AED", "SAR", "HKD", "NZD", "SEK", "NOK", "DKK", "KRW", "BRL",
    "MXN", "ZAR", "RUB", "TRY", "THB", "IDR", "MYR", "PHP", "VND", "ILS",
    "NGN", "PLN", "CZK", "HUF", "TWD",
)

_CODE_ALIASES = {"RMB": "CNY", "RS": "INR"}

_DISPLAY_SYMBOL: dict[str, str] = {
    "USD": "$", "INR": "₹", "EUR": "€", "GBP": "£", "JPY": "¥", "KRW": "₩",
    "RUB": "₽", "TRY": "₺", "THB": "฿", "VND": "₫", "ILS": "₪", "NGN": "₦",
    "PHP": "₱", "BRL": "R$", "AUD": "A$", "CAD": "C$", "SGD": "S$",
    "HKD": "HK$", "NZD": "NZ$", "CNY": "CN¥",
}

_NAMES: dict[str, str] = {
    "USD": "US Dollar", "INR": "Indian Rupee", "EUR": "Euro",
    "GBP": "British Pound", "JPY": "Japanese Yen", "CNY": "Chinese Yuan",
    "AUD": "Australian Dollar", "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc", "SGD": "Singapore Dollar", "AED": "UAE Dirham",
    "SAR": "Saudi Riyal", "HKD": "Hong Kong Dollar",
    "NZD": "New Zealand Dollar", "KRW": "South Korean Won",
    "BRL": "Brazilian Real", "ZAR": "South African Rand",
}

_TOKEN = re.compile(
    "|".join(
        [
            "|".join(
                re.escape(symbol)
                for symbol in sorted(_SYMBOL_TO_CODE, key=len, reverse=True)
            ),
            r"\b(?:" + "|".join(_CODES) + r")\b",
            r"\bRs\.?(?=[\s\d]|$)",
            ]
    )
)

# Used to strip tokens before converting text to a number.
_STRIP_TOKEN = _TOKEN

_MAX_VALUES_SCANNED_PER_COLUMN = 5000


def _token_to_code(token: str) -> str:
    if token in _SYMBOL_TO_CODE:
        return _SYMBOL_TO_CODE[token]
    normalized = token.rstrip(".").upper()
    return _CODE_ALIASES.get(normalized, normalized)


def _codes_in_text(text: str) -> list[str]:
    return [_token_to_code(match.group(0)) for match in _TOKEN.finditer(text)]


def _is_text_column(series: pd.Series) -> bool:
    return series.dtype == object or pd.api.types.is_string_dtype(series)


def _currency_info(code: str | None, *, mixed: bool, found: list[str],
                   source: str, detected: bool) -> dict[str, Any]:
    if mixed:
        return {
            "code": None,
            "symbol": "",
            "name": "Mixed currencies",
            "detected": True,
            "mixed": True,
            "found": found,
            "source": source,
        }
    assert code is not None
    return {
        "code": code,
        "symbol": _DISPLAY_SYMBOL.get(code, code),
        "name": _NAMES.get(code, code),
        "detected": detected,
        "mixed": False,
        "found": found,
        "source": source,
    }


def detect_currency(df: pd.DataFrame, month_cols: list[str]) -> dict[str, Any]:
    """Detect the currency from month-year headers and text cell values."""
    header_counts: Counter[str] = Counter()
    value_counts: Counter[str] = Counter()

    for column in month_cols:
        header_counts.update(_codes_in_text(str(column)))

        if column not in df.columns:
            continue
        series = df[column]
        if not _is_text_column(series):
            continue
        for value in series.dropna().head(_MAX_VALUES_SCANNED_PER_COLUMN):
            if isinstance(value, str):
                value_counts.update(_codes_in_text(value))

    found = sorted(set(header_counts) | set(value_counts))

    if not found:
        return _currency_info("USD", mixed=False, found=[], source="assumed",
                              detected=False)

    if header_counts and value_counts:
        source = "both"
    elif header_counts:
        source = "headers"
    else:
        source = "values"

    if len(found) > 1:
        return _currency_info(None, mixed=True, found=found, source=source,
                              detected=True)

    return _currency_info(found[0], mixed=False, found=found, source=source,
                          detected=True)


def _text_to_number(value: Any) -> float:
    """Convert '$1,200.50', '(3,400)', '1.234,56 €', '12,5' ... to a float."""
    if value is None:
        return float("nan")
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)

    text = str(value).strip().replace("\u00a0", " ")
    if not text:
        return float("nan")

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    text = _STRIP_TOKEN.sub("", text).replace(" ", "").strip()

    if text.endswith("-") or text.endswith("\u2212"):
        negative = True
        text = text[:-1]
    if text.startswith(("-", "\u2212")):
        negative = True
        text = text[1:]
    elif text.startswith("+"):
        text = text[1:]

    if not text:
        return float("nan")

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            # 1.234,56 -> European style, comma is the decimal mark
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        if re.fullmatch(r"\d{1,3}(,\d{3})+", text):
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")

    try:
        number = float(text)
    except ValueError:
        return float("nan")
    return -number if negative else number


def coerce_text_amounts(df: pd.DataFrame, month_cols: list[str]) -> pd.DataFrame:
    """
    Return a frame whose month-year columns are numeric.

    Columns that already hold numbers are untouched; text columns are cleaned
    (currency symbols/codes and separators removed) and converted. The input
    frame is never modified.
    """
    to_convert = [
        column
        for column in dict.fromkeys(month_cols)
        if column in df.columns and _is_text_column(df[column])
    ]
    if not to_convert:
        return df

    converted = df.copy()
    for column in to_convert:
        converted[column] = df[column].map(_text_to_number).astype("float64")
    return converted