"""Testes de pending.json. Ver docs/08-modelo-de-dados.md §5.1, UC-10 FE-01/FE-02."""

from __future__ import annotations

from cronista.client import local_state


def test_sem_pending_json_lista_vazia(tmp_path):
    assert local_state.list_pending(tmp_path) == []


def test_mark_pendente_envio_persiste_reuniao_e_trilhas(tmp_path):
    meeting = {"id": "abc", "title": "Reunião", "tracks": [{"speaker": "voce"}]}
    local_state.mark_pendente_envio(tmp_path, meeting)

    pendentes = local_state.list_pending(tmp_path)
    assert len(pendentes) == 1
    assert pendentes[0]["estado"] == "pendente_envio"
    assert pendentes[0]["id"] == "abc"
    assert pendentes[0]["tracks"] == [{"speaker": "voce"}]


def test_mark_falha_envio_distingue_de_pendente_envio(tmp_path):
    meeting = {"id": "abc", "title": "Reunião"}
    local_state.mark_falha_envio(tmp_path, meeting, tracks_faltantes=[{"speaker": "outros"}])

    entry = local_state.list_pending(tmp_path)[0]
    assert entry["estado"] == "falha_envio"
    assert entry["tracks_faltantes"] == [{"speaker": "outros"}]


def test_clear_remove_pendencia(tmp_path):
    local_state.mark_pendente_envio(tmp_path, {"id": "abc"})
    local_state.clear(tmp_path, "abc")

    assert local_state.list_pending(tmp_path) == []


def test_clear_id_inexistente_nao_levanta(tmp_path):
    local_state.clear(tmp_path, "nao-existe")  # não deve levantar
    assert local_state.list_pending(tmp_path) == []


def test_mark_falha_envio_sobrescreve_pendente_envio_anterior(tmp_path):
    # UC-10 FA-01: a reunião evolui de um estado local pro outro à medida
    # que o registro avança, não acumula entradas duplicadas.
    local_state.mark_pendente_envio(tmp_path, {"id": "abc"})
    local_state.mark_falha_envio(tmp_path, {"id": "abc"}, tracks_faltantes=[])

    pendentes = local_state.list_pending(tmp_path)
    assert len(pendentes) == 1
    assert pendentes[0]["estado"] == "falha_envio"
