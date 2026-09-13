"""Testes de cronista.client.session_info -- usado pela tela estática de
`cronista` sem comando, fora de terminal interativo (`cli.py`)."""

from __future__ import annotations

import jwt

from cronista.client import session_info


def test_usuario_logado_sem_token_salvo(monkeypatch):
    monkeypatch.setattr(session_info.token_store, "load_tokens", lambda: None)

    assert session_info.usuario_logado() == "não autenticado"


def test_usuario_logado_decodifica_sub_do_token(monkeypatch):
    token = jwt.encode(
        {"sub": "cronista"}, "segredo-de-teste-com-comprimento-adequado", algorithm="HS256"
    )
    monkeypatch.setattr(
        session_info.token_store,
        "load_tokens",
        lambda: {"access_token": token, "refresh_token": "x"},
    )

    assert session_info.usuario_logado() == "cronista"


def test_usuario_logado_token_corrompido_nao_quebra(monkeypatch):
    monkeypatch.setattr(
        session_info.token_store,
        "load_tokens",
        lambda: {"access_token": "isso-nao-e-um-jwt", "refresh_token": "x"},
    )

    assert session_info.usuario_logado() == "autenticado"
