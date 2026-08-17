"""Nome da pasta de uma reunião em disco. Ver docs/08-modelo-de-dados.md §2.

Formato: AAAA-MM-DD_HHMM_titulo-em-slug — o exemplo que a própria spec já
usava (2026-08-12_1430_reuniao-comercial), nunca antes implementado como
código. Sem acento, sem espaço: é nome de pasta, não texto pra humano ler
(RF-06, UC-03 FA-01).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

_MAX_SLUG_LENGTH = 50
_FALLBACK_SLUG = "reuniao"


def slugify(text: str) -> str:
    # Decompõe acento (á -> a + ´) e descarta as marcas combinantes.
    normalized = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))

    lowered = without_accents.lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")

    if not hyphenated:
        return _FALLBACK_SLUG
    return hyphenated[:_MAX_SLUG_LENGTH].rstrip("-")


def make_audio_dir(title: str, started_at: datetime) -> str:
    return f"{started_at:%Y-%m-%d_%H%M}_{slugify(title)}"
