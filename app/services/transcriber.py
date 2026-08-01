"""
Social Pulse API — Audio Transcription Service
Transcribes audio files into text using faster-whisper.
"""
import os
import logging

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Exception raised when audio transcription fails."""
    pass


def transcribe_audio(audio_path: str, model_size: str = "tiny") -> str:
    """
    Transcribe an audio file using faster-whisper.
    Returns the complete text transcript.
    """
    if not os.path.exists(audio_path):
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    try:
        from faster_whisper import WhisperModel
        
        # Initialize model with CPU float32/int8 fallback for universal compatibility
        try:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
        except Exception:
            model = WhisperModel(model_size, device="cpu", compute_type="float32")

        segments, info = model.transcribe(audio_path, beam_size=5)

        transcript_parts = []
        for segment in segments:
            # Optionally format with timestamps if needed
            timestamp = f"[{int(segment.start // 60):02d}:{int(segment.start % 60):02d}]"
            transcript_parts.append(f"{timestamp} {segment.text.strip()}")

        full_transcript = "\n".join(transcript_parts)
        if not full_transcript.strip():
            raise TranscriptionError("Transcription yielded empty text.")

        return full_transcript
    except ImportError:
        raise TranscriptionError("faster-whisper is not installed or available.")
    except Exception as e:
        logger.error(f"Whisper transcription failed: {str(e)}")
        # If faster-whisper fails due to missing CTranslate2 or model loading issues, raise clean exception
        raise TranscriptionError(f"Audio transcription error: {str(e)}")
