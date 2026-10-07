"""
Pydantic schemas used at the API boundary.

These schemas describe the JSON contract between:
    React <-> FastAPI
"""

from typing import Any

from pydantic import BaseModel


class DatasetProcessResponse(BaseModel):
    status: str
    data: dict[str, Any] | None = None
    clarifications: list[dict[str, Any]] = []


class ErrorResponse(BaseModel):
    detail: str