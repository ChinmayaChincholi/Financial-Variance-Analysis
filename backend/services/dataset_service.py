"""
Dataset application service.

Responsibilities:
- receive uploaded Excel files
- inspect workbook sheets
- materialize uploads temporarily
- run ingestion
- resolve clarification choices
- trigger complete precomputation
- stream real processing stages to the frontend
"""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
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
    """
    Read the uploaded file while the FastAPI UploadFile is
    still alive and copy it to a temporary file.

    IMPORTANT:
    This must happen before returning a StreamingResponse.
    FastAPI may close UploadFile after the route returns.
    """

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

    temporary_path = temporary_file.name

    try:
        temporary_file.write(
            file_bytes
        )
        temporary_file.close()

    except Exception:
        temporary_file.close()

        try:
            Path(
                temporary_path
            ).unlink(
                missing_ok=True
            )
        except OSError:
            pass

        raise

    return (
        temporary_path,
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

    return list(
        workbook.sheet_names
    )


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
        _cleanup(
            temporary_path
        )


def _clarification_response(
        ingestion_result,
        filename: str,
        sheet_name: str,
) -> dict:
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


def _process_materialized_dataset(
        temporary_path: str,
        filename: str,
        sheet_name: str | None,
        progress_callback: Callable[
                               [str],
                               None,
                           ] | None = None,
) -> dict:
    """
    Process an already-materialized Excel file.

    This function is synchronous because pandas and the analysis
    engine perform CPU/blocking work.

    It is executed in a worker thread by the async service.
    """

    def emit(
            stage: str,
    ) -> None:
        if progress_callback is not None:
            progress_callback(
                stage
            )

    # ---------------------------------------------------------
    # Stage 1
    # ---------------------------------------------------------

    emit(
        "Importing dataset"
    )

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

    # ---------------------------------------------------------
    # Stage 2
    # ---------------------------------------------------------

    emit(
        "Detecting columns"
    )

    ingestion_result = run_ingestion(
        path=temporary_path,
        sheet_name=sheet_name,
    )

    if (
            ingestion_result.status
            == "needs_clarification"
    ):
        return _clarification_response(
            ingestion_result,
            filename,
            sheet_name,
        )

    # ---------------------------------------------------------
    # Stages 3 + 4
    #
    # precompute_dataset() emits the real project-wise and
    # region-wise stage transitions.
    # ---------------------------------------------------------

    session = precompute_dataset(
        file_path=temporary_path,
        sheet_name=sheet_name,
        ingestion_result=ingestion_result,
        filename=filename,
        progress_callback=progress_callback,
    )

    # ---------------------------------------------------------
    # Stage 5
    # ---------------------------------------------------------

    emit(
        "Finalizing results"
    )

    return {
        "status": "resolved",
        "session": session.to_dict(),
    }


async def process_dataset(
        file: UploadFile,
        sheet_name: str | None = None,
) -> dict:
    """
    Non-streaming processing endpoint.

    Kept for compatibility and backend testing.
    The frontend uses stream_process_dataset().
    """

    temporary_path, filename = (
        await _materialize_upload(file)
    )

    try:
        return await asyncio.to_thread(
            _process_materialized_dataset,
            temporary_path,
            filename,
            sheet_name,
        )

    finally:
        _cleanup(
            temporary_path
        )


async def _stream_materialized_dataset(
        temporary_path: str,
        filename: str,
        sheet_name: str | None,
) -> AsyncIterator[str]:
    """
    Stream processing events from an already-materialized file.

    IMPORTANT:
    The UploadFile is NOT used here.

    The uploaded file was already copied to temporary_path before
    this generator was passed to StreamingResponse.
    """

    queue: asyncio.Queue[
        dict
    ] = asyncio.Queue()

    loop = asyncio.get_running_loop()

    def emit(
            stage: str,
    ) -> None:
        """
        Called by the synchronous worker thread.

        The callback safely schedules the event onto the
        asyncio event loop.
        """

        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "progress",
                "stage": stage,
            },
        )

    async def worker() -> None:
        try:
            result = await asyncio.to_thread(
                _process_materialized_dataset,
                temporary_path,
                filename,
                sheet_name,
                emit,
            )

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "result",
                    "data": result,
                },
            )

        except Exception as exc:

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "error",
                    "message": str(exc),
                },
            )

        finally:
            _cleanup(
                temporary_path
            )

    asyncio.create_task(
        worker()
    )

    try:

        while True:

            event = await queue.get()

            yield (
                    json.dumps(
                        event
                    )
                    + "\n"
            )

            if event["type"] in {
                "result",
                "error",
            }:
                break

    except asyncio.CancelledError:

        # The client/browser may disconnect while processing.
        #
        # The worker owns cleanup of the temporary file, so we
        # do not delete it from this generator.

        raise


async def stream_process_dataset(
        file: UploadFile,
        sheet_name: str | None = None,
) -> AsyncIterator[str]:
    """
    Prepare the upload BEFORE returning the streaming generator.

    This is the critical fix for:

        ValueError: read of closed file

    FastAPI can close UploadFile after the route returns.
    Therefore UploadFile.read() must happen here, before the
    StreamingResponse is created.
    """

    temporary_path: str | None = None

    try:

        # -----------------------------------------------------
        # CRITICAL:
        # Read UploadFile NOW, while it is still open.
        # -----------------------------------------------------

        temporary_path, filename = (
            await _materialize_upload(file)
        )

        # -----------------------------------------------------
        # After this point the generator only works with the
        # temporary filesystem path.
        # It never touches UploadFile again.
        # -----------------------------------------------------

        return _stream_materialized_dataset(
            temporary_path,
            filename,
            sheet_name,
        )

    except Exception:

        if temporary_path is not None:
            _cleanup(
                temporary_path
            )

        raise


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
            return _clarification_response(
                ingestion_result,
                filename,
                sheet_name,
            )

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
        _cleanup(
            temporary_path
        )