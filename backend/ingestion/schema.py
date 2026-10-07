"""
Schemas exchanged by the ingestion layer and the application layer.

The ingestion layer produces a resolved ColumnMapping or asks the user
for clarification. Nothing downstream needs to know how the mapping
was derived.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ColumnMapping(BaseModel):
    """
    Actual column names resolved from the uploaded dataset.
    """

    project_col: str
    region_col: Optional[str] = None

    revenue_month_year_cols: list[str] = Field(default_factory=list)
    cost_month_year_cols: list[str] = Field(default_factory=list)

    @field_validator("cost_month_year_cols")
    @classmethod
    def no_overlap_between_revenue_and_cost(
            cls,
            cost_cols: list[str],
            info,
    ) -> list[str]:
        revenue_cols = info.data.get(
            "revenue_month_year_cols",
            [],
        )

        overlap = set(revenue_cols) & set(cost_cols)

        if overlap:
            raise ValueError(
                "The following column(s) were mapped as BOTH "
                f"revenue and cost, which isn't valid: "
                f"{sorted(overlap)}"
            )

        return cost_cols

    def has_revenue(self) -> bool:
        return bool(self.revenue_month_year_cols)

    def has_cost(self) -> bool:
        return bool(self.cost_month_year_cols)

    def has_region(self) -> bool:
        return self.region_col is not None


class ColumnCandidateOut(BaseModel):
    """
    Candidate shown to the user during clarification.
    """

    column: str
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    sample_values: list = Field(default_factory=list)


class ClarificationRequest(BaseModel):
    """
    One unresolved ingestion decision.

    field values used by the application include:

    - header_row
    - project_name
    - region
    - metric_block_0
    - metric_block_1
    - ...

    allow_none=True is used for the optional Region field.
    """

    field: str
    message: str
    candidates: list[ColumnCandidateOut] = Field(
        default_factory=list
    )
    allow_none: bool = False


class IngestionResult(BaseModel):
    """
    Result of ingestion for one workbook sheet.
    """

    status: str

    column_mapping: Optional[ColumnMapping] = None

    clarifications: list[ClarificationRequest] = Field(
        default_factory=list
    )

    header_row_index: Optional[int] = None
    header_row_confidence: Optional[float] = None