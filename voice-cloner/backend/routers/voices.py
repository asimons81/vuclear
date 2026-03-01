"""
POST   /api/v1/voices     — upload + create voice profile
GET    /api/v1/voices     — list profiles
DELETE /api/v1/voices/{voice_id} — delete profile + files
"""
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from backend.config import settings
from backend.services import voice_service
from backend.services.audio_pipeline import preprocess_reference, validate_audio_file

router = APIRouter(prefix="/api/v1/voices", tags=["voices"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


class VoiceProfileResponse(BaseModel):
    voice_id: str
    name: str
    duration_s: float
    created_at: str
    engine: str


@router.post("", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_voice(
    request: Request,
    file: Annotated[UploadFile, File(description="Reference audio (WAV/MP3/OGG/M4A/FLAC, max 50MB)")],
    name: Annotated[str, Form(min_length=1, max_length=80)],
    consent: Annotated[bool, Form(description="Must be true — confirms voice ownership/permission")],
):
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must confirm you own or have permission to clone this voice.",
        )

    # Read upload into temp file
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum 50MB.",
        )

    with tempfile.NamedTemporaryFile(
        suffix=Path(file.filename or "upload.wav").suffix, delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Validate file type and duration
        try:
            _, raw_duration = validate_audio_file(tmp_path)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        # Create a temporary voice_id placeholder to get the output path
        import uuid
        voice_id = str(uuid.uuid4())
        voice_dir = settings.voices_dir / voice_id
        voice_dir.mkdir(parents=True, exist_ok=True)
        ref_path = voice_dir / "reference.wav"

        # Preprocess: normalize → trim → [denoise] → 16kHz mono WAV
        try:
            duration_s = preprocess_reference(tmp_path, ref_path, denoise=settings.denoise)
        except (ValueError, RuntimeError) as e:
            shutil.rmtree(voice_dir, ignore_errors=True)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        # Persist profile (pass voice_id so service uses the dir we already created)
        ip = request.client.host if request.client else "unknown"
        ip_hash = voice_service.hash_ip(ip)

        profile = voice_service.create_voice_profile(
            name=name,
            consent=True,
            duration_s=duration_s,
            ip_hash=ip_hash,
            engine=settings.voice_engine,
            voice_id=voice_id,
        )

        return VoiceProfileResponse(**profile)

    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("", response_model=list[VoiceProfileResponse])
async def list_voices():
    profiles = voice_service.list_voice_profiles()
    return [VoiceProfileResponse(**p) for p in profiles]


@router.delete("/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice(voice_id: str, request: Request):
    ip = request.client.host if request.client else "unknown"
    ip_hash = voice_service.hash_ip(ip)
    deleted = voice_service.delete_voice_profile(voice_id, ip_hash)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice not found")
