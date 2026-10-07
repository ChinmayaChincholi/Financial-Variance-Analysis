"""
Dataset application service.

Responsibilities:
- receive uploaded Excel files
- inspect workbook sheets
- materialize uploads temporarily
- run ingestion
- resolve clarification choices
- trigger complete precomputation
"""

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
from fastapi import UploadFile

from ingestion.column_matching_pipeline import (
    resolve_ingestion_with_choices,
    run_ingestion,
)
from services.precomputation_service import (
    precompute_dataset,
)

ALLOWED_EXTENSIONS = {
    ".xlsx",
    ".xls",
}


def _validate_filename(
        filename: str | None,
) -> str:
    if not filename:
        raise ValueError(
            "No filename was provided."
        )

    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Unsupported file type. Please upload "
            "an Excel file (.xlsx or .xls)."
        )

    return suffix


async def _materialize_upload(
        file: UploadFile,
) -> tuple[str, str]:
    suffix = _validate_filename(
        file.filename
    )

    file_bytes = await file.read()

    if not file_bytes:
        raise ValueError(
            "The uploaded file is empty."
        )

    temporary_file = NamedTemporaryFile(
        suffix=suffix,
        delete=False,
    )

    try:
        temporary_file.write(file_bytes)
        temporary_file.close()
    except Exception:
        temporary_file.close()

        try:
            Path(
                temporary_file.name
            ).unlink(
                missing_ok=True
            )
        except OSError:
            pass

        raise

    return (
        temporary_file.name,
        file.filename or "dataset.xlsx",
    )


def _cleanup(
        temporary_path: str,
) -> None:
    try:
        Path(
            temporary_path
        ).unlink(
            missing_ok=True
        )
    except OSError:
        pass


def _read_workbook_sheets(
        path: str,
) -> list[str]:
    workbook = pd.ExcelFile(path)

    if not workbook.sheet_names:
        raise ValueError(
            "The Excel workbook contains no sheets."
        )

    return list(workbook.sheet_names)


async def inspect_workbook(
        file: UploadFile,
) -> dict:
    temporary_path, filename = (
        await _materialize_upload(file)
    )

    try:
        sheets = _read_workbook_sheets(
            temporary_path
        )

        return {
            "status": "success",
            "filename": filename,
            "sheets": sheets,
        }

    finally:
        _cleanup(temporary_path)


async def process_dataset(
        file: UploadFile,
        sheet_name: str | None = None,
) -> dict:
    temporary_path, filename = (
        await _materialize_upload(file)
    )

    try:
        sheets = _read_workbook_sheets(
            temporary_path
        )

        if sheet_name is None:
            if len(sheets) > 1:
                return {
                    "status": "needs_sheet_selection",
                    "filename": filename,
                    "sheets": sheets,
                }

            sheet_name = sheets[0]

        if sheet_name not in sheets:
            raise ValueError(
                f"Sheet '{sheet_name}' does not exist "
                f"in the workbook."
            )

        ingestion_result = run_ingestion(
            path=temporary_path,
            sheet_name=sheet_name,
        )

        if (
                ingestion_result.status
                == "needs_clarification"
        ):
            return {
                "status": "needs_clarification",
                "filename": filename,
                "sheet_name": sheet_name,
                "clarifications": [
                    clarification.model_dump()
                    for clarification
                    in ingestion_result.clarifications
                ],
                "header_row_index": (
                    ingestion_result.header_row_index
                ),
                "header_row_confidence": (
                    ingestion_result.header_row_confidence
                ),
            }

        session = precompute_dataset(
            file_path=temporary_path,
            sheet_name=sheet_name,
            ingestion_result=ingestion_result,
            filename=filename,
        )

        return {
            "status": "resolved",
            "session": session.to_dict(),
        }

    finally:
        _cleanup(temporary_path)


async def resolve_dataset(
        file: UploadFile,
        sheet_name: str,
        choices_json: str,
) -> dict:
    temporary_path, filename = (
        await _materialize_upload(file)
    )

    try:
        sheets = _read_workbook_sheets(
            temporary_path
        )

        if sheet_name not in sheets:
            raise ValueError(
                f"Sheet '{sheet_name}' does not exist "
                f"in the workbook."
            )

        try:
            choices = json.loads(
                choices_json
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid clarification choices."
            ) from exc

        if not isinstance(
                choices,
                dict,
        ):
            raise ValueError(
                "Clarification choices must be "
                "a JSON object."
            )

        normalized_choices = {
            str(key): str(value)
            for key, value in choices.items()
        }

        ingestion_result = (
            resolve_ingestion_with_choices(
                path=temporary_path,
                sheet_name=sheet_name,
                choices=normalized_choices,
            )
        )

        if (
                ingestion_result.status
                == "needs_clarification"
        ):
            return {
                "status": "needs_clarification",
                "filename": filename,
                "sheet_name": sheet_name,
                "clarifications": [
                    clarification.model_dump()
                    for clarification
                    in ingestion_result.clarifications
                ],
                "header_row_index": (
                    ingestion_result.header_row_index
                ),
                "header_row_confidence": (
                    ingestion_result.header_row_confidence
                ),
            }

        session = precompute_dataset(
            file_path=temporary_path,
            sheet_name=sheet_name,
            ingestion_result=ingestion_result,
            filename=filename,
        )

        return {
            "status": "resolved",
            "session": session.to_dict(),
        }

    finally:
        _cleanup(temporary_path)