"""
Application-level dataset session.

This is the complete precomputed object sent to the frontend after
successful ingestion.
"""

from dataclasses import dataclass
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
        }