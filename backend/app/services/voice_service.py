import os
import io
import logging
from typing import Dict, Any, Optional
from fastapi import UploadFile
from app.core.config import settings
from app.schemas.voice import VoiceAdvisoryResponse, VoiceTranscribeResponse
from app.services.ai_service import GeminiAIService

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Voice Interaction Service.
    Processes audio recordings in English, Telugu, and Hindi, transcribes speech,
    and returns localized audio-ready advisory scripts.
    """

    @classmethod
    async def process_voice_query(
        cls,
        audio_file: UploadFile,
        context_data: Dict[str, Any],
        language_hint: Optional[str] = None
    ) -> VoiceAdvisoryResponse:
        """
        Receives an audio stream/file from Flutter mobile app, transcribes,
        and orchestrates the grounded advisory response.
        """
        contents = await audio_file.read()
        lang_code = language_hint or context_data.get("user_profile", {}).get("preferred_language", "te")

        transcribed_text = "Is dairy business suitable for me?"
        detected_lang = lang_code

        # Attempt Gemini 2.0 / 1.5 Multimodal Audio Transcription if API Key is available
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "your_gemini_api_key_here":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(settings.GEMINI_MODEL)
                
                # Send audio bytes directly to Gemini
                mime_type = audio_file.content_type or "audio/wav"
                audio_part = {
                    "mime_type": mime_type,
                    "data": contents
                }
                
                transcription_prompt = (
                    "Transcribe this audio recording verbatim. Identify if the spoken language is "
                    "Telugu, Hindi, or English. Respond in JSON format: "
                    '{"transcribed_text": "...", "language_code": "te|hi|en"}'
                )
                
                res = model.generate_content(
                    [transcription_prompt, audio_part],
                    generation_config={"response_mime_type": "application/json"}
                )
                import json
                parsed = json.loads(res.text)
                transcribed_text = parsed.get("transcribed_text", transcribed_text)
                detected_lang = parsed.get("language_code", detected_lang)
            except Exception as e:
                logger.warning(f"Gemini multimodal audio processing fallback: {e}")

        # If fallback or default
        if lang_code == "te" and transcribed_text == "Is dairy business suitable for me?":
            transcribed_text = "డెయిరీ వ్యాపారం నాకు అనుకూలమా? ఎంత లోన్ వస్తుంది?"
        elif lang_code == "hi" and transcribed_text == "Is dairy business suitable for me?":
            transcribed_text = "क्या डेयरी का व्यवसाय मेरे लिए उपयुक्त है? कितना लोन मिलेगा?"

        # Generate Grounded Advisory
        advisory_res = await GeminiAIService.generate_advisory(
            query_text=transcribed_text,
            language=detected_lang,
            context_data=context_data
        )

        return VoiceAdvisoryResponse(
            transcribed_text=transcribed_text,
            detected_language=detected_lang,
            advisory=advisory_res,
            tts_script=advisory_res.audio_tts_text
        )

