"""
Dataset HTTP endpoints.

The route layer handles HTTP concerns only.
Dataset processing belongs to services.dataset_service.
"""

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import (
    StreamingResponse,
)

from services.dataset_service import (
    inspect_workbook,
    process_dataset,
    resolve_dataset,
    stream_process_dataset,
)


router = APIRouter(
    prefix="/api/dataset",
    tags=["Dataset"],
)


@router.post("/sheets")
async def inspect_uploaded_workbook(
        file: UploadFile = File(...),
):
    try:

        return await inspect_workbook(
            file
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
                "An unexpected error occurred "
                "while inspecting the workbook."
            ),
        ) from exc


@router.post("/process")
async def process_uploaded_dataset(
        file: UploadFile = File(...),
        sheet_name: str | None = Form(
            default=None
        ),
):
    try:

        return await process_dataset(
            file,
            sheet_name=sheet_name,
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
                "An unexpected error occurred "
                "while processing the dataset."
            ),
        ) from exc


@router.post("/process/stream")
async def stream_uploaded_dataset(
        file: UploadFile = File(...),
        sheet_name: str | None = Form(
            default=None
        ),
):
    """
    Stream real processing stages.

    IMPORTANT:
    stream_process_dataset() first reads the UploadFile and
    materializes it to a temporary file BEFORE this route returns
    the StreamingResponse.

    Therefore the stream never tries to read an already-closed
    FastAPI UploadFile.
    """

    try:

        stream = await stream_process_dataset(
            file,
            sheet_name=sheet_name,
        )

        return StreamingResponse(
            stream,
            media_type=(
                "application/x-ndjson"
            ),
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
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
                "An unexpected error occurred "
                "while preparing dataset processing."
            ),
        ) from exc


@router.post("/resolve")
async def resolve_uploaded_dataset(
        file: UploadFile = File(...),
        sheet_name: str = Form(...),
        choices: str = Form(...),
):
    try:

        return await resolve_dataset(
            file=file,
            sheet_name=sheet_name,
            choices_json=choices,
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
                "An unexpected error occurred "
                "while resolving the dataset."
            ),
        ) from exc