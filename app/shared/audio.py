import io
import logging

from app.shared.llm import client

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_bytes: bytes, filename: str = "answer.wav") -> str:
    """
    Transcribe audio bytes using Groq's Whisper API.
    """
    try:
        # Pass a tuple (filename, file_like_object) to the Groq SDK
        response = await client.audio.transcriptions.create(
            file=(filename, io.BytesIO(audio_bytes)),
            model="whisper-large-v3",
            response_format="json",
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error transcribing audio with Groq: {e}")
        raise e
