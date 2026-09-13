"""Informação de sessão mostrada na tela inicial fora de terminal
interativo: banner, subtítulo, categorias, usuário autenticado + máquina
(`cli.py::_tela_inicial_partes`)."""

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
    assinatura, o cliente nunca tem o JWT_SECRET. Isto é só cosmético."""
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
    de comandos, que cada tela monta do seu próprio jeito."""
    banner_text = banner.render(console)
    banner_text.no_wrap = True  # sem isso, Rich quebra o banner no meio da linha
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
