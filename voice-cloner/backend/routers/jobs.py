"""
GET /api/v1/jobs/{job_id} — poll job status
GET /api/v1/jobs          — list all jobs
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.services import job_service

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class JobResponse(BaseModel):
    job_id: str
    voice_id: str
    status: str
    progress_pct: int
    output_id: Optional[str]
    error: Optional[str]
    created_at: str


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse(**job)


@router.get("", response_model=list[JobResponse])
async def list_jobs():
    jobs = job_service.list_jobs()
    return [JobResponse(**j) for j in jobs]
