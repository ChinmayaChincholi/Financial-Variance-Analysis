"""
The contract between the NLP/column-matching layer and everything
downstream (ingestion/date_ranges.py, analysis/*).

The NLP layer's entire job, from the rest of the system's point of
view, is to produce one of these. Nothing downstream cares HOW the
mapping was derived (embeddings, heuristics, human confirmation of an
ambiguous match, etc.) -- only that it received one.

CHANGE from the original version of this file: region_col is now
Optional[str]. The spec explicitly allows a dataset to have no Region
column at all (Project-wise analysis still works in that case) -- the
ingestion layer needs to be able to produce a valid, complete
ColumnMapping without one, rather than being forced to either invent a
value or fail outright.
"""

from typing import Optional

from pydantic import BaseModel, field_validator


class ColumnMapping(BaseModel):
    """
    Resolved column names for one uploaded dataset, ready to be passed
    directly into analysis/project_wise.py, analysis/region_wise.py,
    and ingestion/date_ranges.py.

    project_col : the actual column name in the client's dataset
    corresponding to Project Name. Always required -- per the spec, no
    analysis (including region-wise) can run without it.
    region_col : the actual column name corresponding to Region, or
    None if the dataset has no such column. Callers must check for
    None before offering Region-wise Analysis (see the spec's deferred-
    warning behavior for a missing Region column).
    revenue_month_year_cols / cost_month_year_cols : the actual column
    names corresponding to Revenue and Cost Month-Year data,
    respectively. Order does not matter -- every downstream
    function re-derives chronological order from each column
    name's parsed date, not from list order. An empty list means
    that metric isn't present in the dataset at all (e.g. a
    revenue-only dataset has cost_month_year_cols == []) -- the
    caller uses this to show "No columns in dataset in relation to
    cost/revenue" instead of invoking analysis.
    """

    project_col: str
    region_col: Optional[str] = None
    revenue_month_year_cols: list[str] = []
    cost_month_year_cols: list[str] = []

    @field_validator("cost_month_year_cols")
    @classmethod
    def no_overlap_between_revenue_and_cost(cls, cost_cols, info):
        revenue_cols = info.data.get("revenue_month_year_cols", [])
        overlap = set(revenue_cols) & set(cost_cols)
        if overlap:
            raise ValueError(
                f"The following column(s) were mapped as BOTH revenue and "
                f"cost, which isn't valid: {sorted(overlap)}"
            )
        return cost_cols

    def has_revenue(self) -> bool:
        return len(self.revenue_month_year_cols) > 0

    def has_cost(self) -> bool:
        return len(self.cost_month_year_cols) > 0

    def has_region(self) -> bool:
        return self.region_col is not None


class ColumnCandidateOut(BaseModel):
    """One candidate column shown to the user during clarification, with
    enough context (sample values, why it scored the way it did) for a
    human to disambiguate quickly -- see column_matching_pipeline.py."""

    column: str
    score: float
    reasons: list[str] = []
    sample_values: list = []


class ClarificationRequest(BaseModel):
    """One thing the ingestion layer couldn't resolve automatically and
    needs the client to answer, surfaced together on the 'Confirm
    Detected Columns' screen."""

    field: str  # 'header_row' | 'project_name' | 'region' | 'revenue_month_year' | 'cost_month_year' | 'metric_block_labels'
    message: str
    candidates: list[ColumnCandidateOut] = []
    # For metric-block clarifications, each "candidate" is really a block
    # of columns rather than a single column -- represented as one
    # ColumnCandidateOut per block, with `column` holding a display label
    # like "Apr-25 .. Mar-26 (12 columns)" and the real column list kept
    # separately by the caller (see IngestionResult.raw_blocks).


class IngestionResult(BaseModel):
    """Top-level output of the ingestion pipeline for one uploaded sheet."""

    status: str  # 'resolved' | 'needs_clarification'
    column_mapping: Optional[ColumnMapping] = None
    clarifications: list[ClarificationRequest] = []
    header_row_index: Optional[int] = None
    header_row_confidence: Optional[float] = None