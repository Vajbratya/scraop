from __future__ import annotations

import io
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import CurrentUser
from app.core.config import settings
from app.models import TranscriptionResponse, TranscriptionSegment, WordTimestamp
from app.services.stt import transcribe_bytes


router = APIRouter(prefix="/stt", tags=["stt"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    *,
    current_user: CurrentUser,  # require auth
    file: UploadFile = File(...),
    language: str = "pt",
    word_timestamps: bool | None = None,
    vad_filter: bool | None = None,
    beam_size: int | None = None,
    temperature: float | None = None,
    initial_prompt: Optional[str] = None,
) -> Any:
    try:
        audio_bytes = await file.read()
    finally:
        await file.close()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    result = transcribe_bytes(
        audio=audio_bytes,
        language=language,
        word_timestamps=(
            word_timestamps if word_timestamps is not None else settings.STT_ENABLE_WORD_TIMESTAMPS
        ),
        vad_filter=vad_filter if vad_filter is not None else settings.STT_ENABLE_VAD,
        beam_size=beam_size if beam_size is not None else settings.STT_BEAM_SIZE,
        temperature=temperature,
        initial_prompt=initial_prompt,
    )

    return result


