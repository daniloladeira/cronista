"""Armazenamento local dos tokens. Ver docs/10-autenticacao.md §3."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import TypedDict


class Tokens(TypedDict):
    access_token: str
    refresh_token: str


def _token_path() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "cronista"
    root.mkdir(parents=True, exist_ok=True)
    return root / "auth.json"


def save_tokens(access_token: str, refresh_token: str) -> None:
    path = _token_path()
    path.write_text(
        json.dumps({"access_token": access_token, "refresh_token": refresh_token}),
        encoding="utf-8",
    )
    # No Windows, os.chmod só alterna o atributo "somente leitura" — não é
    # controle de acesso por usuário de verdade (isso exigiria ACL via
    # icacls, fora de escopo aqui). Em POSIX restringe ao dono.
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def load_tokens() -> Tokens | None:
    path = _token_path()
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Tokens(access_token=data["access_token"], refresh_token=data["refresh_token"])


def clear_tokens() -> None:
    path = _token_path()
    if path.exists():
        path.unlink()
