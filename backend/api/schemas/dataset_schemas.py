"""
Pydantic schemas for dataset-related API responses.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkbookInspectionResponse(BaseModel):
    status: Literal["success"]
    filename: str
    sheets: list[str] = Field(
        default_factory=list
    )


class DatasetProcessResponse(BaseModel):
    status: Literal[
        "resolved",
        "needs_clarification",
        "needs_sheet_selection",
    ]

    session: dict[str, Any] | None = None

    clarifications: list[
        dict[str, Any]
    ] = Field(default_factory=list)

    sheets: list[str] = Field(
        default_factory=list
    )

    filename: str | None = None

    sheet_name: str | None = None

    header_row_index: int | None = None

    header_row_confidence: float | None = None


class ErrorResponse(BaseModel):
    detail: str