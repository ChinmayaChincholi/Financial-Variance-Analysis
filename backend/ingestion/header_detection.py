"""
Finds the real header row of an uploaded sheet.

Real client exports are frequently NOT "row 0 = headers, row 1 = first
data row". Seen in practice (see Financial_Dataset.xlsx used to validate
this module): a fully blank row 0, then the real headers on row 1, with a
handful of columns carrying a leftover "grand total" numeric value that
lands in row 0 for THOSE columns only (because the export tool merged a
totals row awkwardly). Naively calling pd.read_excel() with the default
header=0 silently turns several column names into stray floats.

This module scores the first few rows of the RAW sheet (no header applied
yet) and picks the row that looks most like a header row: mostly text,
mostly unique, non-empty, and followed immediately by a row that looks
like DATA (a mix of types, not another label-shaped row).

This is a heuristic, not a guarantee -- see confidence. When confidence is
low, the caller (column_matching_pipeline.py) surfaces this to the user
as a clarification request instead of guessing silently.
"""

from dataclasses import dataclass

import pandas as pd

MAX_ROWS_TO_SCAN = 10


@dataclass
class HeaderDetectionResult:
    header_row_index: int
    confidence: float  # 0..1 -- see detect_header_row() for how this is built
    candidate_rows: list[dict]  # every scanned row + its score, for the UI
    # fallback candidates are sorted by score, most-likely first


def _row_values(raw: pd.DataFrame, row_idx: int) -> list:
    return raw.iloc[row_idx].tolist()


def _fraction_nonnull(values: list) -> float:
    if not values:
        return 0.0
    return sum(1 for v in values if pd.notna(v)) / len(values)


def _fraction_stringlike(values: list) -> float:
    nonnull = [v for v in values if pd.notna(v)]
    if not nonnull:
        return 0.0
    stringlike = sum(1 for v in nonnull if isinstance(v, str) and v.strip() != "")
    return stringlike / len(nonnull)


def _fraction_unique(values: list) -> float:
    nonnull = [v for v in values if pd.notna(v)]
    if not nonnull:
        return 0.0
    return len(set(nonnull)) / len(nonnull)


def _looks_like_data_row(values: list) -> float:
    """
    Scores how "data-shaped" a row is: a mix of types (not all-text like a
    header usually is), reasonably filled in. Used to confirm the row
    AFTER a header candidate looks like real data, not another label row.
    """
    nonnull = [v for v in values if pd.notna(v)]
    if not nonnull:
        return 0.0
    numeric_count = sum(1 for v in nonnull if isinstance(v, (int, float)))
    fill_ratio = len(nonnull) / len(values)
    type_mix_score = min(1.0, (numeric_count / len(nonnull)) * 2) if numeric_count else 0.3
    return 0.5 * fill_ratio + 0.5 * type_mix_score


def detect_header_row(
        raw: pd.DataFrame, max_rows_to_scan: int = MAX_ROWS_TO_SCAN
) -> HeaderDetectionResult:
    """
    Parameters
    ----------
    raw : the sheet read with header=None (so row 0 is just data, including
          whatever the real header row's text is).

    Returns
    -------
    HeaderDetectionResult. Treat confidence < 0.55 as "ask the user which
    row is the header" rather than proceeding automatically.
    """
    n_scan = min(max_rows_to_scan, len(raw) - 1) if len(raw) > 1 else 0
    scored_rows = []

    for row_idx in range(max(n_scan, 1)):
        values = _row_values(raw, row_idx)
        nonnull_frac = _fraction_nonnull(values)
        if nonnull_frac == 0:
            scored_rows.append({"row_index": row_idx, "score": 0.0, "preview": values[:8]})
            continue

        stringlike_frac = _fraction_stringlike(values)
        unique_frac = _fraction_unique(values)

        next_row_score = 0.0
        if row_idx + 1 < len(raw):
            next_row_score = _looks_like_data_row(_row_values(raw, row_idx + 1))

        score = (
                0.35 * nonnull_frac
                + 0.30 * stringlike_frac
                + 0.15 * unique_frac
                + 0.20 * next_row_score
        )
        scored_rows.append({"row_index": row_idx, "score": round(score, 4), "preview": values[:8]})

    scored_rows.sort(key=lambda r: r["score"], reverse=True)
    best = scored_rows[0]
    return HeaderDetectionResult(
        header_row_index=best["row_index"],
        confidence=best["score"],
        candidate_rows=scored_rows,
    )


def read_sheet_with_detected_header(
        path: str, sheet_name: str
) -> tuple[pd.DataFrame, HeaderDetectionResult]:
    """
    Reads one sheet, auto-detecting which row holds the real headers.

    Returns the DataFrame built with that header row applied, plus the
    detection result (so the caller can decide whether confidence is high
    enough to proceed automatically).
    """
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    result = detect_header_row(raw)
    df = pd.read_excel(path, sheet_name=sheet_name, header=result.header_row_index)
    return df, result