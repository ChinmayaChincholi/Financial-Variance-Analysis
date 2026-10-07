"""
Domain model representing the complete result of processing one dataset.

This model is independent of FastAPI and React.

It represents the application's internal processed dataset.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class DatasetSession:
    """
    Complete precomputed analysis session.
    """

    sheet_name: str

    mapping: dict[str, Any]

    regions: list[str]

    project_wise: dict[str, Any]

    region_wise: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the session to the JSON-compatible structure consumed
        by the API layer.
        """

        return {
            "sheet_name": self.sheet_name,
            "mapping": self.mapping,
            "regions": self.regions,
            "projectWise": self.project_wise,
            "regionWise": self.region_wise,
        }