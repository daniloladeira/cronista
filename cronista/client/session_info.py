"""Informação de sessão mostrada na tela inicial: banner, subtítulo,
categorias, usuário autenticado + máquina. Compartilhado entre o fallback
não-interativo (`cli.py`) e o menu navegável (`home.py`) -- as duas
telas mostram o mesmo conteúdo, só a lista de comandos embaixo muda de
forma (texto estático vs. `OptionList` navegável)."""

from __future__ import annotations

import socket

import jwt
from rich.console import Console
from rich.text import Text

from cronista.client import banner, token_store

SUBTITLE_COLOR = "#F7ECDA"  # dourado bem claro
MINIMAL_COLOR = "#A6A6A6"  # neutro, mesmo tom de "outros" (signal_bar.py)
SUBTITLE = "Grava, transcreve e resume reuniões localmente."
CATEGORIAS = "transcreva reuniões · resumos automáticos · anotações"


def usuario_logado() -> str:
    """Decodifica o `sub` do access token só pra exibir -- sem verificar
    assinatura, porque não faz sentido validar aqui: o cliente nunca tem
    o JWT_SECRET (ClientSettings é deliberadamente restrito, ver
    core/config.py), e a API já vai recusar o token na próxima chamada
    de rede se ele for inválido de verdade. Isto é só cosmético."""
    tokens = token_store.load_tokens()
    if tokens is None:
        return "não autenticado"
    try:
        payload = jwt.decode(tokens["access_token"], options={"verify_signature": False})
        return str(payload.get("sub", "autenticado"))
    except jwt.PyJWTError:
        return "autenticado"


def partes(console: Console) -> list[Text]:
    """Banner + subtítulo + categorias + usuário/máquina -- sem a lista
    de comandos, que cada tela monta do seu próprio jeito.

    `no_wrap=True` no banner: dentro de um `Static` do Textual, o
    container às vezes reserva menos largura do que os 63+ caracteres
    de cada linha do banner, e sem isso o Rich quebra a linha no meio,
    fragmentando "CRONISTA" em pedaços (achado comparando o SVG
    exportado linha por linha, não presumido)."""
    banner_text = banner.render(console)
    banner_text.no_wrap = True
    banner_text.overflow = "ignore"
    return [
        Text(),
        banner_text,
        Text(),
        Text(SUBTITLE, style=f"bold {SUBTITLE_COLOR}"),
        Text(),
        Text(CATEGORIAS, style=MINIMAL_COLOR),
        Text(),
        Text(f"{usuario_logado()} · {socket.gethostname()}", style=MINIMAL_COLOR),
    ]
