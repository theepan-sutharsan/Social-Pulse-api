"""Focused tests for language-aware audio transcription."""
import sys
import types
from types import SimpleNamespace

from app.services.transcriber import normalize_transcription_language, transcribe_audio
from app.controllers.video_analysis_controller import _transcription_preferences


def test_normalize_transcription_language_aliases():
    assert normalize_transcription_language("Tamil") == "ta"
    assert normalize_transcription_language("ta-IN") == "ta"
    assert normalize_transcription_language("English") == "en"
    assert normalize_transcription_language("unknown") == "auto"


def test_transcription_preferences_require_explicit_language_for_whisper():
    assert _transcription_preferences("auto") == ("auto", None, True)
    assert _transcription_preferences("ta") == ("ta", ["ta", "ta-IN"], False)
    assert _transcription_preferences("en") == ("en", ["en", "en-US", "en-GB"], False)


def test_tamil_transcription_uses_language_and_quality_options(tmp_path, monkeypatch):
    calls = {}

    class FakeWhisperModel:
        def __init__(self, model_size, device, compute_type):
            calls["model"] = (model_size, device, compute_type)

        def transcribe(self, audio_path, **options):
            calls["options"] = options
            segment = SimpleNamespace(start=0, text="வணக்கம் தமிழ்")
            return [segment], SimpleNamespace(language="ta")

    fake_module = types.ModuleType("faster_whisper")
    fake_module.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)

    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"audio")
    result = transcribe_audio(str(audio_path), model_size="small", language="ta")

    assert "வணக்கம் தமிழ்" in result
    assert calls["model"] == ("small", "cpu", "int8")
    assert calls["options"]["language"] == "ta"
    assert calls["options"]["beam_size"] == 8
    assert calls["options"]["best_of"] == 5
    assert calls["options"]["vad_filter"] is True
