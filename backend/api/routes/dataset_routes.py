"""
Dataset-related API routes.

The API layer is responsible only for:
- receiving the HTTP request
- passing the uploaded file to the service layer
- returning the service result

All actual processing belongs to services/.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException

from services.dataset_service import (
    process_dataset,
)


router = APIRouter(
    prefix="/api/dataset",
    tags=["Dataset"],
)


@router.post("/process")
async def process_uploaded_dataset(
        file: UploadFile = File(...),
):
    try:
        return await process_dataset(file)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the dataset.",
        ) from exc