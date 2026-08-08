"""
Social Pulse API — Audio Transcription Service
Transcribes audio files into text using faster-whisper.
Also provides a fast transcript lookup via youtube-transcript-api.
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


def get_youtube_transcript(video_id: str) -> str | None:
    """
    Attempt to fetch an existing YouTube caption transcript for a video.
    Uses youtube-transcript-api — no audio download required.

    Returns:
        str:  The full transcript text joined into a single string, or
        None: if no transcript is available (private, disabled, or no captions).
    """
    if not video_id:
        return None

    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

        try:
            # Prefer English; fall back to any available language
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_transcript(["en", "en-US", "en-GB"])
            except NoTranscriptFound:
                # Use whatever language is available, auto-translated to English
                transcript = transcript_list.find_manually_created_transcript()
        except (NoTranscriptFound, Exception):
            try:
                # Last resort: any generated transcript
                data = YouTubeTranscriptApi.get_transcript(video_id)
                text = " ".join(entry["text"] for entry in data if entry.get("text"))
                return text.strip() if text.strip() else None
            except Exception:
                return None

        data = transcript.fetch()
        # FetchedTranscript is iterable; each item has .text attribute (or dict key 'text')
        parts = []
        for entry in data:
            if hasattr(entry, 'text'):
                parts.append(entry.text)
            elif isinstance(entry, dict) and entry.get('text'):
                parts.append(entry['text'])
        text = " ".join(parts).strip()
        return text if text else None

    except ImportError:
        logger.warning("youtube-transcript-api is not installed. Skipping caption lookup.")
        return None
    except Exception as e:
        logger.debug(f"YouTube transcript fetch skipped for {video_id}: {e}")
        return None
