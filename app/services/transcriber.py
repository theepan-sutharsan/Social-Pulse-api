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


class TranscriptFetchError(Exception):
    """Exception raised when a YouTube caption transcript cannot be fetched."""
    pass


SUPPORTED_TRANSCRIPTION_LANGUAGES = {"auto", "ta", "en"}


def normalize_transcription_language(language: str | None) -> str:
    """Normalize UI/API language values to the codes understood by Whisper."""
    value = (language or "auto").strip().lower().replace("_", "-")
    if value in {"ta", "ta-in", "tamil"}:
        return "ta"
    if value in {"en", "en-us", "en-gb", "english"}:
        return "en"
    return "auto"


def transcribe_audio(
    audio_path: str,
    model_size: str | None = None,
    language: str | None = None,
) -> str:
    """
    Transcribe an audio file using faster-whisper.
    Returns the complete text transcript.
    """
    if not os.path.exists(audio_path):
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    try:
        from faster_whisper import WhisperModel
        
        selected_model = model_size or os.getenv("WHISPER_MODEL", "small")
        selected_language = normalize_transcription_language(language)

        # Initialize model with CPU int8/float32 fallback for universal compatibility.
        try:
            model = WhisperModel(selected_model, device="cpu", compute_type="int8")
        except Exception:
            model = WhisperModel(selected_model, device="cpu", compute_type="float32")

        transcribe_options = {
            "beam_size": 8 if selected_language == "ta" else 5,
            "best_of": 5,
            "temperature": 0.0,
            "task": "transcribe",
            "condition_on_previous_text": True,
            "vad_filter": True,
            "vad_parameters": {"min_silence_duration_ms": 500},
        }
        if selected_language != "auto":
            transcribe_options["language"] = selected_language

        segments, info = model.transcribe(audio_path, **transcribe_options)

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


def get_youtube_transcript(
    video_id: str,
    preferred_languages: list[str] | None = None,
    allow_any_language: bool = True,
) -> str | None:
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
        from youtube_transcript_api import YouTubeTranscriptApi

        languages = preferred_languages or ["en", "en-US", "en-GB"]
        try:
            transcript_list = YouTubeTranscriptApi().list(video_id)
        except Exception:
            # Keep compatibility with older youtube-transcript-api releases.
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None

        for finder_name in (
            "find_transcript",
            "find_manually_created_transcript",
            "find_generated_transcript",
        ):
            finder = getattr(transcript_list, finder_name, None)
            if not finder:
                continue
            try:
                transcript = finder(languages)
            except Exception:
                continue
            if transcript:
                break

        # In Tamil/English modes, do not silently select an unrelated caption
        # track. This lets the caller use the language-locked Whisper fallback.
        if transcript is None and allow_any_language:
            try:
                transcript = next(iter(transcript_list), None)
            except Exception:
                transcript = None
        if transcript is None:
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


def fetch_youtube_transcript_only(
    video_id: str,
    preferred_languages: list[str] | None = None,
    allow_any_language: bool = True,
) -> dict:
    """Fetch a YouTube caption transcript without downloading audio or using Whisper.

    This is intentionally separate from :func:`get_youtube_transcript`, which is
    used by AI analysis as a best-effort fast path.  The transcript tab needs a
    deterministic caption-only operation so callers receive a useful error when
    the video has no captions instead of silently falling back to audio
    transcription.

    Returns a JSON-safe mapping containing the combined text, language, and
    timestamped segments.
    """
    if not video_id:
        raise TranscriptFetchError("A valid YouTube video URL is required.")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise TranscriptFetchError(
            "youtube-transcript-api is not installed. Run: pip install youtube-transcript-api"
        ) from exc

    try:
        # v1.x exposes an instance API (``api.list``); retain the classmethod
        # fallback for older deployments that may still be running it.
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
    except Exception:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        except Exception as exc:
            logger.info("No YouTube transcript list available for %s: %s", video_id, exc)
            raise TranscriptFetchError(
                "No YouTube transcript or captions are available for this video."
            ) from exc

    selected = None
    preferred_languages = preferred_languages or ["en", "en-US", "en-GB"]

    # Prefer manually-created captions, then generated captions, and finally
    # the first available language so non-English videos remain usable.
    for finder_name in ("find_manually_created_transcript", "find_generated_transcript", "find_transcript"):
        finder = getattr(transcript_list, finder_name, None)
        if not finder:
            continue
        try:
            selected = finder(preferred_languages)
        except Exception:
            continue
        if selected:
            break

    if selected is None and allow_any_language:
        try:
            selected = next(iter(transcript_list), None)
        except Exception:
            selected = None

    if selected is None:
        raise TranscriptFetchError("No YouTube transcript or captions are available for this video.")

    try:
        fetched = selected.fetch()
    except Exception as exc:
        logger.info("YouTube transcript fetch failed for %s: %s", video_id, exc)
        raise TranscriptFetchError(
            "Unable to fetch the YouTube transcript for this video."
        ) from exc

    segments = []
    for entry in fetched:
        if hasattr(entry, "text"):
            text = getattr(entry, "text", "") or ""
            start = getattr(entry, "start", 0) or 0
            duration = getattr(entry, "duration", 0) or 0
        elif isinstance(entry, dict):
            text = entry.get("text", "") or ""
            start = entry.get("start", 0) or 0
            duration = entry.get("duration", 0) or 0
        else:
            continue

        text = str(text).strip()
        if not text:
            continue
        try:
            start = float(start)
        except (TypeError, ValueError):
            start = 0.0
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            duration = 0.0
        segments.append({"text": text, "start": start, "duration": duration})

    if not segments:
        raise TranscriptFetchError("The YouTube transcript is empty.")

    return {
        "text": "\n".join(segment["text"] for segment in segments),
        "language": getattr(selected, "language_code", None),
        "segments": segments,
    }
