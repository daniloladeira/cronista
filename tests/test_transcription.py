"""Testes de cronista.worker.transcription com um modelo falso — sem GPU,
sem baixar modelo real. A validação com faster-whisper de verdade roda à
parte, no worker em container (docs/12-transcricao.md §3, §7).
"""

from __future__ import annotations

from types import SimpleNamespace

from cronista.worker import transcription


class _FakeModel:
    def __init__(self, segments: list[SimpleNamespace]) -> None:
        self._segments = segments
        self.calls: list[tuple[str, dict]] = []

    def transcribe(self, path: str, **kwargs: object):
        self.calls.append((path, kwargs))
        return iter(self._segments), SimpleNamespace(language="pt")


def _segment(start: float, end: float, text: str) -> SimpleNamespace:
    return SimpleNamespace(start=start, end=end, text=text)


def test_transcribe_track_converts_seconds_to_ms_and_strips_text() -> None:
    model = _FakeModel([_segment(0.0, 1.5, " olá"), _segment(1.5, 3.2, "tudo bem ")])

    result = transcription.transcribe_track(model, "voce.wav", language="pt")

    assert result == [
        transcription.TranscribedSegment(start_ms=0, end_ms=1500, text="olá"),
        transcription.TranscribedSegment(start_ms=1500, end_ms=3200, text="tudo bem"),
    ]


def test_transcribe_track_empty_when_all_silence() -> None:
    # Trilha de loopback muda enquanto só o usuário fala (docs/12 §3) — o
    # VAD descarta tudo e não deve sobrar segmento nenhum.
    model = _FakeModel([])

    result = transcription.transcribe_track(model, "outros.wav", language="pt")

    assert result == []


def test_transcribe_track_always_enables_vad() -> None:
    model = _FakeModel([])

    transcription.transcribe_track(model, "voce.wav", language="pt")

    assert model.calls[0][1]["vad_filter"] is True


def test_transcribe_track_fixes_language() -> None:
    model = _FakeModel([])

    transcription.transcribe_track(model, "voce.wav", language="pt")

    assert model.calls[0][1]["language"] == "pt"


def test_transcribe_track_passes_vocabulary_as_initial_prompt() -> None:
    model = _FakeModel([])

    transcription.transcribe_track(
        model, "voce.wav", language="pt", vocabulary="Cronista, WER"
    )

    assert model.calls[0][1]["initial_prompt"] == "Cronista, WER"


def test_transcribe_track_empty_vocabulary_means_no_prompt() -> None:
    model = _FakeModel([])

    transcription.transcribe_track(model, "voce.wav", language="pt")

    assert model.calls[0][1]["initial_prompt"] is None


def test_load_model_uses_shared_cache_dir_and_params(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeWhisperModel:
        def __init__(self, model_size: str, **kwargs: object) -> None:
            captured["model_size"] = model_size
            captured.update(kwargs)

    monkeypatch.setattr(transcription, "WhisperModel", _FakeWhisperModel)

    transcription.load_model("large-v3", "int8_float16")

    assert captured["model_size"] == "large-v3"
    assert captured["compute_type"] == "int8_float16"
    assert captured["download_root"] == transcription.MODEL_CACHE_DIR
