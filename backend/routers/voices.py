"""
POST   /api/v1/voices     — upload + create voice profile
GET    /api/v1/voices     — list profiles
DELETE /api/v1/voices/{voice_id} — delete profile + files
"""
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from backend.config import settings
from backend.services import voice_service
from backend.services.audio_pipeline import preprocess_reference, validate_audio_file

router = APIRouter(prefix="/api/v1/voices", tags=["voices"])
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


class VoiceSampleResponse(BaseModel):
    sample_id: str
    kind: str
    duration_s: float
    note: str | None = None
    filename: str
    created_at: str


class VoiceProfileResponse(BaseModel):
    voice_id: str
    name: str
    duration_s: float
    created_at: str
    engine: str
    sample_count: int = 1
    total_duration_s: float = 0.0
    samples: list[VoiceSampleResponse] = Field(default_factory=list)


@router.post("", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_voice(
    request: Request,
    file: Annotated[UploadFile, File(description="Reference audio (WAV/MP3/OGG/M4A/FLAC, max 50MB)")],
    name: Annotated[str, Form(min_length=1, max_length=80)],
    consent: Annotated[bool, Form(description="Must be true — confirms voice ownership/permission")],
):
    origin = request.headers.get("origin")
    client_host = request.client.host if request.client else "unknown"
    logger.info(
        "Voice upload request received | origin=%s client=%s filename=%s content_type=%s",
        origin,
        client_host,
        file.filename,
        file.content_type,
    )

    if not consent:
        logger.warning("Voice upload rejected: consent not granted | filename=%s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must confirm you own or have permission to clone this voice.",
        )

    tmp_path: Path | None = None
    voice_dir: Path | None = None

    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        size_bytes = len(content)
        logger.info(
            "Voice upload payload read | filename=%s size_bytes=%d",
            file.filename,
            size_bytes,
        )

        if size_bytes > MAX_UPLOAD_BYTES:
            logger.warning(
                "Voice upload rejected: file too large | filename=%s size_bytes=%d",
                file.filename,
                size_bytes,
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum 50MB.",
            )

        with tempfile.NamedTemporaryFile(
            suffix=Path(file.filename or "upload.wav").suffix, delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        logger.info("Voice upload temp file written | path=%s", tmp_path)

        try:
            logger.info("Voice upload validation starting | path=%s", tmp_path)
            detected_mime, raw_duration = validate_audio_file(tmp_path)
            logger.info(
                "Voice upload validation complete | path=%s mime=%s duration_s=%.2f",
                tmp_path,
                detected_mime,
                raw_duration,
            )
        except ValueError as e:
            logger.warning(
                "Voice upload validation failed | filename=%s detail=%s",
                file.filename,
                e,
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        import uuid

        voice_id = str(uuid.uuid4())
        voice_dir = settings.voices_dir / voice_id
        voice_dir.mkdir(parents=True, exist_ok=True)
        ref_path = voice_dir / "reference.wav"

        try:
            logger.info(
                "Voice upload preprocess starting | voice_id=%s src=%s dst=%s denoise=%s",
                voice_id,
                tmp_path,
                ref_path,
                settings.denoise,
            )
            duration_s = preprocess_reference(tmp_path, ref_path, denoise=settings.denoise)
            logger.info(
                "Voice upload preprocess complete | voice_id=%s duration_s=%.2f",
                voice_id,
                duration_s,
            )
        except (ValueError, RuntimeError) as e:
            logger.warning(
                "Voice upload preprocess failed | voice_id=%s detail=%s",
                voice_id,
                e,
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        ip_hash = voice_service.hash_ip(client_host)

        logger.info("Voice upload profile save starting | voice_id=%s name=%s", voice_id, name)
        profile = voice_service.create_voice_profile(
            name=name,
            consent=True,
            duration_s=duration_s,
            ip_hash=ip_hash,
            engine=settings.voice_engine,
            voice_id=voice_id,
        )
        logger.info("Voice upload profile save complete | voice_id=%s", voice_id)

        return VoiceProfileResponse(**profile)
    except HTTPException:
        if voice_dir is not None:
            shutil.rmtree(voice_dir, ignore_errors=True)
        raise
    except Exception:
        if voice_dir is not None:
            shutil.rmtree(voice_dir, ignore_errors=True)
        logger.exception("Voice upload failed with unhandled exception | filename=%s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Voice profile creation failed.",
        )
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


@router.get("", response_model=list[VoiceProfileResponse])
async def list_voices():
    profiles = voice_service.list_voice_profiles()
    return [VoiceProfileResponse(**p) for p in profiles]


@router.post("/{voice_id}/samples", response_model=VoiceSampleResponse, status_code=status.HTTP_201_CREATED)
async def add_voice_sample(
    voice_id: str,
    file: Annotated[UploadFile, File(description="Additional reference audio")],
    note: Annotated[str | None, Form(default=None, max_length=160)] = None,
):
    profile = voice_service.get_voice_profile(voice_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice not found")

    tmp_path: Path | None = None
    sample_dir: Path | None = None

    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum 50MB.",
            )

        with tempfile.NamedTemporaryFile(
            suffix=Path(file.filename or "sample.wav").suffix, delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        detected_mime, duration_s = validate_audio_file(tmp_path)
        if detected_mime not in {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/ogg", "audio/flac", "audio/webm", "video/webm", "audio/mp4", "audio/x-m4a", "video/mp4"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unsupported file type: {detected_mime}")

        sample = voice_service.add_voice_sample(
            voice_id,
            duration_s=duration_s,
            kind="additional",
            note=note,
            source_path=tmp_path,
        )
        return VoiceSampleResponse(**sample)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


@router.delete("/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice(voice_id: str, request: Request):
    ip = request.client.host if request.client else "unknown"
    ip_hash = voice_service.hash_ip(ip)
    deleted = voice_service.delete_voice_profile(voice_id, ip_hash)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice not found")
