"""
GET    /api/v1/outputs                          — list all outputs
GET    /api/v1/outputs/{output_id}/download     — download WAV or MP3
DELETE /api/v1/outputs/{output_id}              — delete output
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.services import output_service

router = APIRouter(prefix="/api/v1/outputs", tags=["outputs"])


class OutputResponse(BaseModel):
    output_id: str
    job_id: str
    voice_id: str
    script: str
    duration_s: float
    created_at: str


@router.get("", response_model=list[OutputResponse])
async def list_outputs():
    outputs = output_service.list_outputs()
    return [OutputResponse(**o) for o in outputs]


@router.get("/{output_id}/download")
async def download_output(
    output_id: str,
    format: str = Query(default="wav", pattern="^(wav|mp3)$"),
):
    output = output_service.get_output(output_id)
    if not output:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output not found")

    file_path = output_service.get_output_file(output_id, format)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Output file ({format}) not found",
        )

    media_type = "audio/wav" if format == "wav" else "audio/mpeg"
    filename = f"voice-clone-{output_id[:8]}.{format}"
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )


@router.delete("/{output_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_output(output_id: str):
    deleted = output_service.delete_output(output_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output not found")
