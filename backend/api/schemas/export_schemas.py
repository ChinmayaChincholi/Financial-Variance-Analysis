"""
Schemas for Excel export requests.
"""

from typing import Any

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(
        default_factory=list
    )

    columns: list[str] = Field(
        default_factory=list
    )

    filename: str = "analysis.xlsx"

    sheet_name: str = "Analysis"