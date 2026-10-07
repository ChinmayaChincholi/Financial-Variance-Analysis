"""
Excel export API.

This endpoint ONLY formats already-computed frontend data.
It performs no financial analysis.
"""

import re

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from api.schemas.export_schemas import (
    ExportRequest,
)
from export.excel_exporter import (
    export_dataframe_to_excel_bytes,
)

router = APIRouter(
    prefix="/api/export",
    tags=["Export"],
)


def _safe_filename(
        filename: str,
) -> str:
    cleaned = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        filename.strip(),
    )

    if not cleaned:
        cleaned = "analysis.xlsx"

    if not cleaned.lower().endswith(".xlsx"):
        cleaned += ".xlsx"

    return cleaned


def _safe_sheet_name(
        sheet_name: str,
) -> str:
    cleaned = re.sub(
        r'[\[\]:*?/\\]',
        "_",
        sheet_name.strip(),
    )

    if not cleaned:
        cleaned = "Analysis"

    return cleaned[:31]


@router.post("/excel")
async def export_excel(
        request: ExportRequest,
):
    try:
        if request.columns:
            df = pd.DataFrame(
                request.rows,
                columns=request.columns,
            )
        else:
            df = pd.DataFrame(
                request.rows
            )

        workbook_bytes = (
            export_dataframe_to_excel_bytes(
                df=df,
                sheet_name=_safe_sheet_name(
                    request.sheet_name
                ),
            )
        )

        filename = _safe_filename(
            request.filename
        )

        return Response(
            content=workbook_bytes,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                )
            },
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not generate the Excel export."
            ),
        ) from exc