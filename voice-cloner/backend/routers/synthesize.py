"""
POST /api/v1/synthesize — queue a synthesis job
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.services import job_service, voice_service

router = APIRouter(prefix="/api/v1/synthesize", tags=["synthesize"])

MAX_SCRIPT_CHARS = 2000


class SynthesizeRequest(BaseModel):
    voice_id: str
    script: str = Field(min_length=1, max_length=MAX_SCRIPT_CHARS)
    speed: float = Field(default=1.0, ge=0.7, le=1.3)
    pause_ms: int = Field(default=300, ge=0, le=1000)


class SynthesizeResponse(BaseModel):
    job_id: str
    status: str


@router.post("", response_model=SynthesizeResponse, status_code=status.HTTP_202_ACCEPTED)
async def synthesize(req: SynthesizeRequest):
    # Validate voice exists
    profile = voice_service.get_voice_profile(req.voice_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voice profile not found: {req.voice_id}",
        )

    ref = voice_service.get_reference_wav(req.voice_id)
    if not ref:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reference audio missing for this voice profile",
        )

    # Create job and submit
    job = job_service.create_job(
        voice_id=req.voice_id,
        script=req.script.strip(),
        speed=req.speed,
        pause_ms=req.pause_ms,
    )

    job_service.submit_job(job["job_id"])

    return SynthesizeResponse(job_id=job["job_id"], status=job["status"])
