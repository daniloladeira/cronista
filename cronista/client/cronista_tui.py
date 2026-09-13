"""Ponte pro `cronista-tui` (Ink/Node) -- navegação (menu inicial,
dispositivos, lista, abrir reunião, busca), ADR-0017.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ENTRY = _REPO_ROOT / "cronista-tui" / "src" / "index.js"
_NODE_MODULES = _REPO_ROOT / "cronista-tui" / "node_modules"


class TuiError(Exception):
    """cronista-tui não pôde ser iniciado (Node ausente, dependências não
    instaladas)."""


def run(
    section: str | None = None, *, meeting_id: str | None = None, search_term: str | None = None
) -> None:
    """Abre o cronista-tui, opcionalmente já na `section`/`meeting_id`/
    `search_term` pedida (env vars, lidos por `cronista-tui/src/App.js`).
    Sem `section`, mostra a home."""
    node = shutil.which("node")
    if node is None:
        raise TuiError(
            "Node.js não encontrado no PATH -- cronista-tui (o menu e a "
            "navegação de dispositivos/reuniões) depende dele. Instale com "
            "`winget install OpenJS.NodeJS` ou https://nodejs.org."
        )
    if not _NODE_MODULES.is_dir():
        raise TuiError(
            f"Dependências do cronista-tui não instaladas. Rode `npm install` em {_ENTRY.parent.parent}."
        )

    env = dict(os.environ)
    if section is not None:
        env["CRONISTA_TUI_SECTION"] = section
    if meeting_id is not None:
        env["CRONISTA_TUI_MEETING_ID"] = meeting_id
    if search_term is not None:
        env["CRONISTA_TUI_SEARCH_TERM"] = search_term

    # Sem redirecionar stdio: Ink precisa do TTY real do processo pai.
    subprocess.run([node, str(_ENTRY)], env=env, cwd=str(_ENTRY.parent.parent))
