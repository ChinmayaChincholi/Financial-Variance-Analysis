"""
Dataset application service.

Responsibilities:
- receive an uploaded Excel file
- temporarily store it
- run ingestion
- trigger precomputation when ingestion succeeds
- return a complete DatasetSession

This module does NOT implement:
- column scoring
- period parsing
- financial formulas
- variance selection
- Excel formatting

Those responsibilities belong to their respective modules.
"""

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import UploadFile

from ingestion.column_matching_pipeline import run_ingestion
from services.precomputation_service import precompute_dataset


async def process_dataset(file: UploadFile) -> dict:
    """
    Process an uploaded Excel dataset.

    Workflow:

        Upload
           ↓
        Temporary file
           ↓
        Ingestion
           ↓
        Precomputation
           ↓
        DatasetSession
    """

    if not file.filename:
        raise ValueError("No filename was provided.")

    suffix = Path(file.filename).suffix.lower()

    if suffix not in {".xlsx", ".xls"}:
        raise ValueError(
            "Unsupported file type. Please upload an Excel file."
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    temporary_path = None

    try:
        with NamedTemporaryFile(
                suffix=suffix,
                delete=False,
        ) as temporary_file:
            temporary_file.write(file_bytes)
            temporary_path = temporary_file.name

        # For now, use the first sheet.
        #
        # A dedicated workbook/sheet-selection service can be introduced
        # when the multi-sheet selection UI is integrated.
        import pandas as pd

        workbook = pd.ExcelFile(temporary_path)

        if not workbook.sheet_names:
            raise ValueError("The Excel workbook contains no sheets.")

        sheet_name = workbook.sheet_names[0]

        ingestion_result = run_ingestion(
            path=temporary_path,
            sheet_name=sheet_name,
        )

        if ingestion_result.status == "needs_clarification":
            return {
                "status": "needs_clarification",
                "clarifications": [
                    clarification.model_dump()
                    for clarification in ingestion_result.clarifications
                ],
            }

        if ingestion_result.column_mapping is None:
            raise ValueError(
                "Ingestion completed without producing a column mapping."
            )

        session = precompute_dataset(
            file_path=temporary_path,
            sheet_name=sheet_name,
            ingestion_result=ingestion_result,
        )

        return {
            "status": "resolved",
            "data": session.to_dict(),
        }

    finally:
        if temporary_path:
            try:
                Path(temporary_path).unlink(missing_ok=True)
            except OSError:
                pass