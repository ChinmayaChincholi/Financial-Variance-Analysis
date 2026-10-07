"""
Builds a ColumnProfile for every column in the (already header-detected)
dataset: cardinality, dtype shape, sample values, and whether the header
itself parses as a Month-Year date. This is the shared feature set that
column_scoring.py and metric_block_resolver.py both score against -- no
scoring logic lives here, only measurement.
"""

import re
from dataclasses import dataclass, field

import pandas as pd

from ingestion.period_grouping import parse_month_year_column

MAX_SAMPLE_VALUES = 8

# Any column filled below this fraction is treated as structurally empty
# -- a stray artifact (e.g. one stray typed value past the real data
# range in the source spreadsheet), not a real field. This matters
# because such columns can otherwise slip through: e.g. a genuinely
# blank column named "Unnamed: 62" (pandas's placeholder for a column
# with no real header at all) was found, during testing, to get
# fuzzy-date-parsed as the year 2062 (dateutil reads ": 62" as a 2-digit
# year) purely because parse_month_year_column now uses fuzzy=True (see
# period_grouping.py) -- a false positive from a column that should
# never have been considered a candidate for anything in the first
# place, given it has almost no data in it at all.
MIN_FILL_RATIO = 0.01

_UNNAMED_PATTERN = re.compile(r"^unnamed:\s*\d+$", re.IGNORECASE)


def drop_placeholder_or_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes columns that aren't real data at all, before any profiling
    or matching happens: pandas's "Unnamed: N" placeholder for a column
    with no real header, OR any column filled below MIN_FILL_RATIO
    (checked independently -- a genuinely empty column with a real-
    looking header should still be dropped, and a placeholder header
    with a little real data should still be dropped).
    """
    keep_cols = []
    for col in df.columns:
        name = str(col)
        is_placeholder_name = bool(_UNNAMED_PATTERN.match(name.strip()))
        fill_ratio = df[col].notna().mean() if len(df) else 0.0
        if is_placeholder_name or fill_ratio < MIN_FILL_RATIO:
            continue
        keep_cols.append(col)
    return df[keep_cols]


@dataclass
class ColumnProfile:
    name: str
    position: int  # 0-based index in df.columns, used for block-contiguity
    non_null_count: int
    total_count: int
    distinct_count: int
    is_numeric: bool
    is_text: bool
    sample_values: list = field(default_factory=list)
    is_month_year: bool = False
    parsed_year: int | None = None
    parsed_month: int | None = None

    @property
    def fill_ratio(self) -> float:
        return self.non_null_count / self.total_count if self.total_count else 0.0

    @property
    def cardinality_ratio(self) -> float:
        """distinct values / non-null rows -- low means a repeating category
        column (region-shaped), high means many distinct values (id/name
        -shaped)."""
        return self.distinct_count / self.non_null_count if self.non_null_count else 0.0


def _is_month_year_header(name: str) -> tuple[bool, int | None, int | None]:
    try:
        year, month = parse_month_year_column(str(name))
        return True, year, month
    except ValueError:
        return False, None, None


def profile_columns(df: pd.DataFrame) -> list[ColumnProfile]:
    """
    Profiles every column of df. Column order in the returned list matches
    df.columns order -- callers that need positional/contiguity logic
    (metric_block_resolver.py) rely on this.
    """
    profiles = []
    total = len(df)

    for position, col in enumerate(df.columns):
        series = df[col]
        non_null = series.dropna()
        distinct_values = non_null.unique().tolist()

        is_numeric = pd.api.types.is_numeric_dtype(series)
        is_text = not is_numeric and non_null.map(lambda v: isinstance(v, str)).all() if len(non_null) else False

        is_my, year, month = _is_month_year_header(str(col))

        sample = distinct_values[:MAX_SAMPLE_VALUES]

        profiles.append(
            ColumnProfile(
                name=str(col),
                position=position,
                non_null_count=len(non_null),
                total_count=total,
                distinct_count=len(set(distinct_values)),
                is_numeric=is_numeric,
                is_text=is_text,
                sample_values=sample,
                is_month_year=is_my,
                parsed_year=year,
                parsed_month=month,
            )
        )

    return profiles


def co_occurrence_spread(df: pd.DataFrame, candidate_col: str, detail_cols: list[str]) -> float:
    """
    For a fixed value of candidate_col, how much do the given detail_cols
    vary underneath it, on average? Used as the "many resources/rows
    share one project" signal from the spec: a true Project Name column
    should have several distinct values in genuinely row-level detail
    columns (e.g. Resource Name, Emp ID) underneath each project.

    Returns a 0..1-ish score: mean(distinct detail values per group) /
    mean group size, capped at 1.0. 0 means every group has exactly one
    detail value (candidate_col is itself a fine-grained/unique key, not
    a grouping column); values closer to 1 mean strong internal variety.
    """
    if not detail_cols or candidate_col not in df.columns:
        return 0.0
    valid_detail_cols = [c for c in detail_cols if c in df.columns and c != candidate_col]
    if not valid_detail_cols:
        return 0.0

    grouped = df.groupby(candidate_col, sort=False)
    group_sizes = grouped.size()
    if group_sizes.empty or group_sizes.mean() <= 1:
        return 0.0

    distinct_counts = grouped[valid_detail_cols].nunique().mean(axis=1)
    ratio = (distinct_counts / group_sizes).clip(upper=1.0)
    return float(ratio.mean())


def pick_detail_columns_for_cooccurrence(profiles: list[ColumnProfile], exclude: set[str], max_cols: int = 2) -> list[str]:
    """
    Auto-selects the highest-cardinality text/id-like columns (other than
    the candidate itself) to correlate against in co_occurrence_spread,
    instead of hardcoding column names like "Resource Name". Picks
    columns with high cardinality_ratio -- id/name-shaped columns are
    exactly the ones that vary a lot underneath a real grouping column.
    """
    candidates = [
        p for p in profiles
        if p.name not in exclude and p.non_null_count > 0 and (p.is_text or not p.is_numeric)
    ]
    candidates.sort(key=lambda p: p.cardinality_ratio, reverse=True)
    return [p.name for p in candidates[:max_cols]]