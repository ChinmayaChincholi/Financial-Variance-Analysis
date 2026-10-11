"""
Application-level dataset session.

This is the complete precomputed object that is persisted as a workspace and
served to the frontend. The frontend never asks the backend to perform
analysis after this point; it only reads the session.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DatasetSession:
    filename: str
    sheet_name: str
    row_count: int
    column_count: int
    mapping: dict[str, Any]
    regions: list[str]
    periods: dict[str, Any]
    project_wise: dict[str, Any]
    region_wise: dict[str, Any]
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": {
                "filename": self.filename,
                "sheet_name": self.sheet_name,
                "row_count": self.row_count,
                "column_count": self.column_count,
            },
            "mapping": self.mapping,
            "regions": self.regions,
            "periods": self.periods,
            "projectWise": self.project_wise,
            "regionWise": self.region_wise,
            "summary": self.summary,
        }