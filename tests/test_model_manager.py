"""Testes de cronista.worker.model_manager (docs/12-transcricao.md §8, §9).
`load_model` é mockado -- a carga real (GPU, large-v3) já foi validada à
parte, na etapa de infra do worker."""

from __future__ import annotations

import pytest

from cronista.core.config import WorkerSettings
from cronista.worker import model_manager as mm


@pytest.fixture
def settings(tmp_path) -> WorkerSettings:
    return WorkerSettings(
        database_url="unused",
        data_root=str(tmp_path),
        whisper_model="large-v3",
        whisper_compute_type="int8_float16",
        whisper_language="pt",
        whisper_fallback_compute_type="int8",
        whisper_idle_unload_seconds=300,
    )


def test_is_out_of_memory_reconhece_mensagem_da_ctranslate2() -> None:
    assert mm.is_out_of_memory(RuntimeError("CUDA failed with error out of memory"))
    assert mm.is_out_of_memory(RuntimeError("Out Of Memory"))  # case-insensitive


def test_is_out_of_memory_nao_reconhece_erro_comum() -> None:
    assert not mm.is_out_of_memory(RuntimeError("arquivo não encontrado"))
    assert not mm.is_out_of_memory(ValueError("formato de áudio inválido"))


def test_acquire_carrega_uma_vez_e_reaproveita(monkeypatch, settings) -> None:
    chamadas = []
    monkeypatch.setattr(
        mm, "load_model", lambda model, compute_type, **k: chamadas.append(compute_type) or object()
    )
    manager = mm.ModelManager(settings)

    m1 = manager.acquire()
    m2 = manager.acquire()

    assert m1 is m2
    assert chamadas == ["int8_float16"]  # só carregou uma vez


def test_acquire_oom_no_load_tenta_fallback_uma_vez(monkeypatch, settings) -> None:
    chamadas = []

    def fake_load(model, compute_type, **k):
        chamadas.append(compute_type)
        if compute_type == settings.whisper_compute_type:
            raise RuntimeError("CUDA failed with error out of memory")
        return object()

    monkeypatch.setattr(mm, "load_model", fake_load)
    manager = mm.ModelManager(settings)

    result = manager.acquire()

    assert result is not None
    assert chamadas == ["int8_float16", "int8"]


def test_acquire_oom_no_load_mesmo_no_fallback_propaga(monkeypatch, settings) -> None:
    def fake_load(model, compute_type, **k):
        raise RuntimeError("CUDA failed with error out of memory")

    monkeypatch.setattr(mm, "load_model", fake_load)
    manager = mm.ModelManager(settings)

    with pytest.raises(RuntimeError, match="out of memory"):
        manager.acquire()


def test_acquire_erro_comum_no_load_nao_tenta_fallback(monkeypatch, settings) -> None:
    chamadas = []

    def fake_load(model, compute_type, **k):
        chamadas.append(compute_type)
        raise RuntimeError("modelo não encontrado no cache")

    monkeypatch.setattr(mm, "load_model", fake_load)
    manager = mm.ModelManager(settings)

    with pytest.raises(RuntimeError, match="não encontrado"):
        manager.acquire()
    assert chamadas == ["int8_float16"]  # nunca tentou o fallback


def test_reload_with_fallback_descarrega_e_recarrega(monkeypatch, settings) -> None:
    chamadas = []
    monkeypatch.setattr(
        mm, "load_model", lambda model, compute_type, **k: chamadas.append(compute_type) or object()
    )
    manager = mm.ModelManager(settings)
    original = manager.acquire()

    novo = manager.reload_with_fallback()

    assert novo is not original
    assert chamadas == ["int8_float16", "int8"]


def test_reload_with_fallback_ja_no_fallback_levanta_fallback_exhausted(
    monkeypatch, settings
) -> None:
    monkeypatch.setattr(mm, "load_model", lambda model, compute_type, **k: object())
    manager = mm.ModelManager(settings)
    manager.reload_with_fallback()  # primeira vez: ok, agora está no fallback

    with pytest.raises(mm.FallbackExhausted):
        manager.reload_with_fallback()


def test_release_if_idle_nao_descarrega_antes_do_tempo(monkeypatch, settings) -> None:
    relogio = {"agora": 1000.0}
    monkeypatch.setattr(mm.time, "monotonic", lambda: relogio["agora"])
    monkeypatch.setattr(mm, "load_model", lambda model, compute_type, **k: object())
    manager = mm.ModelManager(settings)
    manager.acquire()

    relogio["agora"] += settings.whisper_idle_unload_seconds - 1

    assert manager.release_if_idle() is False


def test_release_if_idle_descarrega_apos_o_tempo(monkeypatch, settings) -> None:
    relogio = {"agora": 1000.0}
    monkeypatch.setattr(mm.time, "monotonic", lambda: relogio["agora"])
    cargas = []
    monkeypatch.setattr(
        mm, "load_model", lambda model, compute_type, **k: cargas.append(1) or object()
    )
    manager = mm.ModelManager(settings)
    manager.acquire()

    relogio["agora"] += settings.whisper_idle_unload_seconds

    assert manager.release_if_idle() is True
    assert len(cargas) == 1
    # próxima chamada carrega de novo, sob demanda
    manager.acquire()
    assert len(cargas) == 2


def test_release_if_idle_sem_modelo_carregado_nao_faz_nada(settings) -> None:
    manager = mm.ModelManager(settings)

    assert manager.release_if_idle() is False


def test_acquire_reinicia_o_relogio_de_ociosidade(monkeypatch, settings) -> None:
    relogio = {"agora": 1000.0}
    monkeypatch.setattr(mm.time, "monotonic", lambda: relogio["agora"])
    monkeypatch.setattr(mm, "load_model", lambda model, compute_type, **k: object())
    manager = mm.ModelManager(settings)
    manager.acquire()

    relogio["agora"] += settings.whisper_idle_unload_seconds - 1
    manager.acquire()  # uso recente -- reinicia a contagem de ociosidade
    relogio["agora"] += settings.whisper_idle_unload_seconds - 1

    assert manager.release_if_idle() is False
