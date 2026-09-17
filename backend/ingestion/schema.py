"""
The contract between the NLP/column-matching layer and everything
downstream (ingestion/date_ranges.py, analysis/*).

The NLP layer's entire job, from the rest of the system's point of
view, is to produce one of these. Nothing downstream cares HOW the
mapping was derived (embeddings, heuristics, human confirmation of an
ambiguous match, etc.) -- only that it received one.
"""

from pydantic import BaseModel, field_validator


class ColumnMapping(BaseModel):
    """
    Resolved column names for one uploaded dataset, ready to be passed
    directly into analysis/project_wise.py, analysis/region_wise.py,
    and ingestion/date_ranges.py.

    project_col / region_col : the actual column names in the client's
        dataset corresponding to Project Name and Region.
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
    region_col: str
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