"""Testes de cronista.worker.runner contra Postgres real (mesma fixture
`db_session` da API, docs/14-plano-de-testes.md §7). transcribe_track é
mockado — a validação com faster-whisper de verdade já rodou à parte,
contra GPU, na etapa anterior (docs/12-transcricao.md §7)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from cronista.core.config import WorkerSettings
from cronista.core.models import Meeting, Segment, Track
from cronista.worker import runner
from cronista.worker.model_manager import FallbackExhausted
from cronista.worker.transcription import TranscribedSegment


class _FakeModelManager:
    """`transcribe_track` é mockado nesses testes, então a identidade do
    "modelo" nunca importa -- só o número de chamadas e o comportamento
    do fallback, pra testar a retentativa de §9 sem GPU nenhuma."""

    def __init__(self, fallback_raises: bool = False) -> None:
        self.acquire_calls = 0
        self.fallback_calls = 0
        self._fallback_raises = fallback_raises

    def acquire(self) -> object:
        self.acquire_calls += 1
        return object()

    def reload_with_fallback(self) -> object:
        self.fallback_calls += 1
        if self._fallback_raises:
            raise FallbackExhausted("falta de memória já no fallback")
        return object()

    def release_if_idle(self) -> bool:
        return False


def _meeting(**overrides: object) -> Meeting:
    defaults = dict(
        title="Reunião de teste",
        source="capture",
        host="maquina-de-teste",
        audio_dir="2026-08-17_teste",
        expected_tracks=2,
        status="recorded",
        started_at=datetime(2026, 8, 17, 14, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return Meeting(**defaults)


def _track(meeting: Meeting, speaker: str, path: str = "x.wav") -> Track:
    return Track(meeting=meeting, speaker=speaker, path=path, sample_rate=16_000, channels=1)


@pytest.fixture
def worker_settings(tmp_path) -> WorkerSettings:
    return WorkerSettings(
        database_url="unused-aqui-a-sessao-de-teste-ja-vem-pronta",
        data_root=str(tmp_path),
        whisper_model="large-v3",
        whisper_compute_type="int8_float16",
        whisper_language="pt",
        whisper_fallback_compute_type="int8",
    )


def test_claim_next_meeting_devolve_none_quando_fila_vazia(db_session: Session) -> None:
    assert runner.claim_next_meeting(db_session) is None


def test_claim_next_meeting_marca_transcribing(db_session: Session) -> None:
    meeting = _meeting()
    db_session.add(meeting)
    db_session.commit()

    claimed = runner.claim_next_meeting(db_session)

    assert claimed is not None
    assert claimed.id == meeting.id
    assert claimed.status == "transcribing"


def test_claim_next_meeting_ignora_outros_status(db_session: Session) -> None:
    db_session.add(_meeting(status="transcribed"))
    db_session.add(_meeting(status="registering"))
    db_session.commit()

    assert runner.claim_next_meeting(db_session) is None


def test_claim_next_meeting_pega_a_mais_antiga_primeiro(db_session: Session) -> None:
    mais_nova = _meeting(started_at=datetime(2026, 8, 17, 15, 0, tzinfo=timezone.utc))
    mais_antiga = _meeting(started_at=datetime(2026, 8, 17, 10, 0, tzinfo=timezone.utc))
    db_session.add_all([mais_nova, mais_antiga])
    db_session.commit()

    claimed = runner.claim_next_meeting(db_session)

    assert claimed.id == mais_antiga.id


def test_recover_interrupted_devolve_transcribing_para_recorded(db_session: Session) -> None:
    presa = _meeting(status="transcribing")
    intocada = _meeting(status="transcribed")
    db_session.add_all([presa, intocada])
    db_session.commit()

    count = runner.recover_interrupted(db_session)

    db_session.refresh(presa)
    db_session.refresh(intocada)
    assert presa.status == "recorded"
    assert intocada.status == "transcribed"
    assert count == 1


def test_recover_interrupted_devolve_zero_quando_nao_ha_nada_preso(db_session: Session) -> None:
    db_session.add(_meeting(status="recorded"))
    db_session.commit()

    assert runner.recover_interrupted(db_session) == 0


def test_process_meeting_sucesso_persiste_segmentos_mesclados(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    meeting = _meeting(status="transcribing")
    voce = _track(meeting, "voce", path="voce.wav")
    outros = _track(meeting, "outros", path="outros.wav")
    db_session.add(meeting)
    db_session.commit()

    def fake_transcribe_track(model, path, language, vocabulary=""):
        if path.name == "voce.wav":
            return [TranscribedSegment(start_ms=0, end_ms=1000, text="oi")]
        return [TranscribedSegment(start_ms=500, end_ms=1500, text="e aí")]

    monkeypatch.setattr(runner, "transcribe_track", fake_transcribe_track)

    runner.process_meeting(db_session, meeting, model_manager=_FakeModelManager(), settings=worker_settings)

    db_session.refresh(meeting)
    assert meeting.status == "transcribed"
    assert meeting.error is None

    segments = (
        db_session.query(Segment)
        .filter(Segment.meeting_id == meeting.id)
        .order_by(Segment.start_ms)
        .all()
    )
    assert [(s.speaker, s.start_ms, s.text) for s in segments] == [
        ("voce", 0, "oi"),
        ("outros", 500, "e aí"),
    ]
    assert segments[0].track_id == voce.id
    assert segments[1].track_id == outros.id


def test_process_meeting_falha_marca_transcription_failed_sem_apagar_audio(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    meeting = _meeting(status="transcribing")
    _track(meeting, "voce")
    db_session.add(meeting)
    db_session.commit()

    def fake_transcribe_track(model, path, language, vocabulary=""):
        raise RuntimeError("arquivo de áudio corrompido")

    monkeypatch.setattr(runner, "transcribe_track", fake_transcribe_track)
    model_manager = _FakeModelManager()

    runner.process_meeting(db_session, meeting, model_manager=model_manager, settings=worker_settings)

    db_session.refresh(meeting)
    assert meeting.status == "transcription_failed"
    assert meeting.error == "arquivo de áudio corrompido"
    assert db_session.query(Segment).filter(Segment.meeting_id == meeting.id).count() == 0
    # erro comum, não parece OOM -- nunca deveria ter acionado o fallback (§9)
    assert model_manager.fallback_calls == 0


def test_process_meeting_oom_tenta_de_novo_com_fallback_e_consegue(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    meeting = _meeting(status="transcribing")
    _track(meeting, "voce")
    db_session.add(meeting)
    db_session.commit()

    tentativas = {"n": 0}

    def fake_transcribe_track(model, path, language, vocabulary=""):
        tentativas["n"] += 1
        if tentativas["n"] == 1:
            raise RuntimeError("CUDA failed with error out of memory")
        return [TranscribedSegment(start_ms=0, end_ms=1000, text="ok no fallback")]

    monkeypatch.setattr(runner, "transcribe_track", fake_transcribe_track)
    model_manager = _FakeModelManager()

    runner.process_meeting(db_session, meeting, model_manager=model_manager, settings=worker_settings)

    db_session.refresh(meeting)
    assert meeting.status == "transcribed"
    assert model_manager.fallback_calls == 1
    segments = db_session.query(Segment).filter(Segment.meeting_id == meeting.id).all()
    assert [s.text for s in segments] == ["ok no fallback"]


def test_process_meeting_oom_persistente_marca_falha_sem_loop(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # OOM na primeira tentativa E no fallback -- desiste, não tenta um
    # terceiro jeito nem troca de modelo (docs/12 §9).
    meeting = _meeting(status="transcribing")
    _track(meeting, "voce")
    db_session.add(meeting)
    db_session.commit()

    def fake_transcribe_track(model, path, language, vocabulary=""):
        raise RuntimeError("CUDA failed with error out of memory")

    monkeypatch.setattr(runner, "transcribe_track", fake_transcribe_track)
    model_manager = _FakeModelManager(fallback_raises=True)

    runner.process_meeting(db_session, meeting, model_manager=model_manager, settings=worker_settings)

    db_session.refresh(meeting)
    assert meeting.status == "transcription_failed"
    assert "fallback" in meeting.error.lower()
    assert model_manager.fallback_calls == 1


def test_process_meeting_reprocessamento_substitui_segmentos_antigos(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    meeting = _meeting(status="transcribing")
    _track(meeting, "voce")
    db_session.add(meeting)
    db_session.commit()
    db_session.add(
        Segment(meeting_id=meeting.id, speaker="voce", start_ms=0, end_ms=999, text="versão velha")
    )
    db_session.commit()

    def fake_transcribe_track(model, path, language, vocabulary=""):
        return [TranscribedSegment(start_ms=0, end_ms=1000, text="versão nova")]

    monkeypatch.setattr(runner, "transcribe_track", fake_transcribe_track)

    runner.process_meeting(db_session, meeting, model_manager=_FakeModelManager(), settings=worker_settings)

    segments = db_session.query(Segment).filter(Segment.meeting_id == meeting.id).all()
    assert [s.text for s in segments] == ["versão nova"]


def test_run_once_devolve_false_quando_fila_vazia(
    db_session: Session, worker_settings: WorkerSettings
) -> None:
    assert runner.run_once(db_session, model_manager=_FakeModelManager(), settings=worker_settings) is False


def test_run_once_processa_uma_reuniao_e_devolve_true(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    meeting = _meeting()
    _track(meeting, "voce")
    db_session.add(meeting)
    db_session.commit()

    monkeypatch.setattr(
        runner,
        "transcribe_track",
        lambda model, path, language, vocabulary="": [TranscribedSegment(0, 1000, "oi")],
    )

    assert runner.run_once(db_session, model_manager=_FakeModelManager(), settings=worker_settings) is True

    db_session.refresh(meeting)
    assert meeting.status == "transcribed"


class _RespostaHttpFalsa:
    def __init__(self, ok: bool = True) -> None:
        self._ok = ok

    def raise_for_status(self) -> None:
        if not self._ok:
            raise RuntimeError("erro http simulado")


def test_trigger_pending_summaries_desligado_por_padrao_nao_chama_api(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    meeting = _meeting(status="transcribed")
    db_session.add(meeting)
    db_session.commit()
    chamadas = []
    monkeypatch.setattr(runner.httpx2, "post", lambda *a, **k: chamadas.append(1))

    runner.trigger_pending_summaries(db_session, worker_settings)

    assert chamadas == []


def test_trigger_pending_summaries_sem_token_nao_chama_mesmo_com_flag_ligada(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = worker_settings.model_copy(update={"worker_auto_summarize": True})
    meeting = _meeting(status="transcribed")
    db_session.add(meeting)
    db_session.commit()
    chamadas = []
    monkeypatch.setattr(runner.httpx2, "post", lambda *a, **k: chamadas.append(1))

    runner.trigger_pending_summaries(db_session, settings)

    assert chamadas == []


def test_trigger_pending_summaries_chama_a_api_pra_cada_reuniao_transcrita(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = worker_settings.model_copy(
        update={"worker_auto_summarize": True, "worker_service_token": "token-de-teste"}
    )
    m1 = _meeting(status="transcribed", audio_dir="a")
    m2 = _meeting(status="transcribed", audio_dir="b")
    db_session.add_all([m1, m2])
    db_session.commit()
    chamadas = []
    monkeypatch.setattr(
        runner.httpx2,
        "post",
        lambda url, headers, timeout: (chamadas.append((url, headers)), _RespostaHttpFalsa())[1],
    )

    runner.trigger_pending_summaries(db_session, settings)

    assert len(chamadas) == 2
    for url, headers in chamadas:
        assert headers == {"Authorization": "Bearer token-de-teste"}
        assert url.endswith("/summarize")


def test_trigger_pending_summaries_ignora_reunioes_summary_failed(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = worker_settings.model_copy(
        update={"worker_auto_summarize": True, "worker_service_token": "token-de-teste"}
    )
    meeting = _meeting(status="summary_failed")
    db_session.add(meeting)
    db_session.commit()
    chamadas = []
    monkeypatch.setattr(runner.httpx2, "post", lambda *a, **k: chamadas.append(1))

    runner.trigger_pending_summaries(db_session, settings)

    assert chamadas == []


def test_trigger_pending_summaries_falha_http_nao_propaga(
    db_session: Session, worker_settings: WorkerSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = worker_settings.model_copy(
        update={"worker_auto_summarize": True, "worker_service_token": "token-de-teste"}
    )
    meeting = _meeting(status="transcribed")
    db_session.add(meeting)
    db_session.commit()

    def _falha(*args: object, **kwargs: object) -> None:
        raise RuntimeError("conexão recusada")

    monkeypatch.setattr(runner.httpx2, "post", _falha)

    runner.trigger_pending_summaries(db_session, settings)  # não levanta
