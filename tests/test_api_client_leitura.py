"""Testes dos métodos de leitura de cronista.client.api_client (RF-20 a
RF-24, UC-07/UC-08) -- HTTP mockado, o comportamento real do endpoint já
é coberto em tests/test_meeting_detail.py, test_transcript.py,
test_rename.py, test_search.py."""

from __future__ import annotations

import httpx2
import pytest

from cronista.client import api_client, token_store


class _RespostaFalsa:
    def __init__(self, status_code: int, corpo: object) -> None:
        self.status_code = status_code
        self._corpo = corpo

    def json(self) -> object:
        return self._corpo

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx2.Request("GET", "http://teste")
            raise httpx2.HTTPStatusError("erro", request=request, response=self)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _token_falso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        token_store, "load_tokens", lambda: {"access_token": "token-de-teste", "refresh_token": "x"}
    )


def test_list_meetings_chama_get_meetings(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = []
    monkeypatch.setattr(
        httpx2,
        "get",
        lambda url, params=None, headers=None, timeout=None: (
            chamadas.append((url, params)),
            _RespostaFalsa(200, [{"id": "1", "title": "x"}]),
        )[1],
    )

    resultado = api_client.list_meetings()

    assert resultado == [{"id": "1", "title": "x"}]
    assert chamadas[0][0].endswith("/meetings")


def test_get_meeting_chama_o_id_certo(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = []
    monkeypatch.setattr(
        httpx2,
        "get",
        lambda url, params=None, headers=None, timeout=None: (
            chamadas.append(url),
            _RespostaFalsa(200, {"id": "abc", "tracks": [], "summaries": []}),
        )[1],
    )

    resultado = api_client.get_meeting("abc")

    assert resultado["id"] == "abc"
    assert chamadas[0].endswith("/meetings/abc")


def test_get_transcript_devolve_lista(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx2,
        "get",
        lambda url, params=None, headers=None, timeout=None: _RespostaFalsa(
            200, [{"speaker": "voce", "text": "oi"}]
        ),
    )

    resultado = api_client.get_transcript("abc")

    assert resultado == [{"speaker": "voce", "text": "oi"}]


def test_rename_meeting_chama_patch_com_titulo(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = []
    monkeypatch.setattr(
        httpx2,
        "patch",
        lambda url, json=None, headers=None, timeout=None: (
            chamadas.append((url, json)),
            _RespostaFalsa(200, {"id": "abc", "title": json["title"]}),
        )[1],
    )

    resultado = api_client.rename_meeting("abc", "Novo título")

    assert resultado["title"] == "Novo título"
    assert chamadas[0][1] == {"title": "Novo título"}


def test_search_monta_parametros_opcionais(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = []
    monkeypatch.setattr(
        httpx2,
        "get",
        lambda url, params=None, headers=None, timeout=None: (
            chamadas.append(params),
            _RespostaFalsa(200, []),
        )[1],
    )

    api_client.search("decisão", speaker="voce", since="2026-01-01T00:00:00Z")

    assert chamadas[0] == {"q": "decisão", "speaker": "voce", "since": "2026-01-01T00:00:00Z"}


def test_search_sem_filtros_so_manda_q(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = []
    monkeypatch.setattr(
        httpx2,
        "get",
        lambda url, params=None, headers=None, timeout=None: (
            chamadas.append(params),
            _RespostaFalsa(200, []),
        )[1],
    )

    api_client.search("decisão")

    assert chamadas[0] == {"q": "decisão"}


def test_authed_get_sem_token_levanta_erro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_store, "load_tokens", lambda: None)

    with pytest.raises(api_client.ApiError):
        api_client.list_meetings()


def test_authed_get_renova_token_uma_vez_apos_401(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas_get = []
    monkeypatch.setattr(
        httpx2,
        "get",
        lambda url, params=None, headers=None, timeout=None: (
            chamadas_get.append(headers["Authorization"]),
            _RespostaFalsa(401 if len(chamadas_get) == 1 else 200, []),
        )[1],
    )
    monkeypatch.setattr(api_client, "refresh", lambda refresh_token: "token-novo")
    salvos = []
    monkeypatch.setattr(
        token_store, "save_tokens", lambda access, refresh: salvos.append((access, refresh))
    )

    api_client.list_meetings()

    assert chamadas_get == ["Bearer token-de-teste", "Bearer token-novo"]
    assert salvos == [("token-novo", "x")]
