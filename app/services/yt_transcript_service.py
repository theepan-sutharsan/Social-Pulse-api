"""
Social Pulse API — YouTube Transcript Fetching Service (Channel Analysis)
Strategy: youtube-transcript-api first (no quota cost), Faster-Whisper fallback.
This is a batch-friendly version used by the channel analysis feature.
"""
import os
import logging
import tempfile

logger = logging.getLogger(__name__)

# Lazy-loaded Whisper model singleton (loaded once per process)
_whisper_model = None
_whisper_model_size = None


def _get_whisper_model(model_size: str | None = None):
    global _whisper_model, _whisper_model_size
    selected_model = model_size or os.getenv("WHISPER_MODEL", "small")
    if _whisper_model is None or _whisper_model_size != selected_model:
        from faster_whisper import WhisperModel
        try:
            _whisper_model = WhisperModel(selected_model, device="cpu", compute_type="int8")
        except Exception:
            _whisper_model = WhisperModel(selected_model, device="cpu", compute_type="float32")
        _whisper_model_size = selected_model
    return _whisper_model


def get_transcript_for_video(
    video_id: str,
    preferred_languages: list[str] | None = None,
    whisper_language: str | None = None,
    allow_any_language: bool = True,
) -> dict:
    """
    Fetch transcript for a single YouTube video.
    Returns: {text: str|None, source: 'youtube_api'|'whisper'|'failed', language: str|None}

    Strategy:
    1. Try youtube-transcript-api (manual transcripts preferred, then auto-generated)
    2. On failure, fall back to yt-dlp audio download + Faster-Whisper transcription
    """
    if preferred_languages is None:
        preferred_languages = ["en", "ta", "hi", "fr", "de", "es"]

    # --- Strategy 1: YouTube Transcript API ---
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
        )

        ytt = YouTubeTranscriptApi()
        transcript_list = ytt.list(video_id)

        selected = None
        # Try manual transcripts first (higher quality)
        try:
            selected = transcript_list.find_manually_created_transcript(preferred_languages)
        except NoTranscriptFound:
            pass

        # Fall back to auto-generated
        if not selected:
            try:
                selected = transcript_list.find_generated_transcript(preferred_languages)
            except NoTranscriptFound:
                pass

        # In an explicit language mode, do not return an unrelated caption track.
        # That allows the Whisper fallback to transcribe the requested language.
        if not selected and allow_any_language:
            for t in transcript_list:
                selected = t
                break

        if selected:
            fetched = selected.fetch()
            snippets = []
            for item in fetched:
                text = getattr(item, "text", None) or item.get("text", "")
                if text:
                    snippets.append(str(text).strip())
            full_text = " ".join(snippets)
            if full_text.strip():
                return {
                    "text": full_text,
                    "source": "youtube_api",
                    "language": getattr(selected, "language_code", "en"),
                }

    except Exception as e:
        logger.debug(f"youtube-transcript-api failed for {video_id}: {e}")

    # --- Strategy 2: Faster-Whisper fallback ---
    return _transcribe_with_whisper(video_id, language=whisper_language)


def _transcribe_with_whisper(video_id: str, language: str | None = None) -> dict:
    """
    Download audio via yt-dlp and transcribe with Faster-Whisper.
    Uses a temporary file that is cleaned up after transcription.
    """
    tmp_dir = tempfile.mkdtemp(prefix="sp_yt_ch_")
    audio_path = os.path.join(tmp_dir, f"{video_id}.mp3")

    try:
        import subprocess
        result = subprocess.run(
            [
                "yt-dlp",
                "-x", "--audio-format", "mp3",
                "--audio-quality", "5",
                "--quiet",
                "-o", audio_path,
                f"https://www.youtube.com/watch?v={video_id}",
            ],
            check=True,
            capture_output=True,
            timeout=300,
        )

        if not os.path.exists(audio_path):
            # yt-dlp may write with a slightly different name
            candidates = [f for f in os.listdir(tmp_dir) if f.startswith(video_id)]
            if candidates:
                audio_path = os.path.join(tmp_dir, candidates[0])
            else:
                raise FileNotFoundError("Downloaded audio file not found.")

        model = _get_whisper_model()
        transcribe_options = {
            "beam_size": 8 if language == "ta" else 5,
            "best_of": 5,
            "temperature": 0.0,
            "task": "transcribe",
            "condition_on_previous_text": True,
            "vad_filter": True,
            "vad_parameters": {"min_silence_duration_ms": 500},
        }
        if language in {"ta", "en"}:
            transcribe_options["language"] = language
        segments, info = model.transcribe(audio_path, **transcribe_options)
        full_text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())

        if full_text.strip():
            return {
                "text": full_text,
                "source": "whisper",
                "language": getattr(info, "language", "en"),
            }
        return {"text": None, "source": "failed", "language": None}

    except Exception as e:
        logger.warning(f"Whisper transcription failed for {video_id}: {e}")
        return {"text": None, "source": "failed", "language": None}

    finally:
        # Cleanup temporary audio files
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def batch_get_transcripts(video_ids: list[str], max_whisper_fallbacks: int = 5) -> dict[str, dict]:
    """
    Fetch transcripts for a list of video IDs.
    Caps Whisper fallbacks to avoid excessive compute time for channels with many
    videos that lack captions.
    Returns: {video_id: {text, source, language}}
    """
    results: dict[str, dict] = {}
    whisper_count = 0

    for video_id in video_ids:
        try:
            result = get_transcript_for_video(video_id)
        except Exception as e:
            logger.warning(f"Transcript fetch completely failed for {video_id}: {e}")
            result = {"text": None, "source": "failed", "language": None}

        if result.get("source") == "whisper":
            whisper_count += 1

        results[video_id] = result

        # If we've hit the Whisper fallback cap, skip further Whisper calls
        if whisper_count >= max_whisper_fallbacks:
            logger.info(f"Whisper fallback cap ({max_whisper_fallbacks}) reached. Skipping further audio downloads.")
            remaining = [vid for vid in video_ids if vid not in results]
            for vid in remaining:
                results[vid] = {"text": None, "source": "failed", "language": None}
            break

    return results
