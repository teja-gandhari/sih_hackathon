from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from app.schemas.feasibility import AdvisoryQueryResponse


class VoiceTranscribeResponse(BaseModel):
    transcribed_text: str
    detected_language: str  # te, hi, en
    confidence: float


class VoiceAdvisoryResponse(BaseModel):
    transcribed_text: str
    detected_language: str
    advisory: AdvisoryQueryResponse
    tts_script: str

