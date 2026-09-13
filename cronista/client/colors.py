"""Interpolação de cor hex e o shimmer do nome "cronista", compartilhados
entre signal_bar.py e banner.py (docs/17-identidade-visual-cli.md §7).
"""

from __future__ import annotations

import time

from rich.text import Text


def lerp_color(base_hex: str, target_hex: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(base_hex[1:3], 16), int(base_hex[3:5], 16), int(base_hex[5:7], 16)
    r2, g2, b2 = int(target_hex[1:3], 16), int(target_hex[3:5], 16), int(target_hex[5:7], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def shimmer_position(
    started_at: float, word_len: int, flash_width: float, sweep_seconds: float, pause_seconds: float
) -> float:
    """Centro do brilho, em índice de caractere da palavra. Roda num ciclo
    varredura+pausa; fora da palavra durante a pausa, pra segurar um
    instante na cor sólida antes de repetir (docs/17 §7)."""
    cycle = sweep_seconds + pause_seconds
    elapsed = (time.monotonic() - started_at) % cycle
    if elapsed > sweep_seconds:
        return -999.0
    span = word_len + 2 * flash_width
    return -flash_width + span * (elapsed / sweep_seconds)


def shimmer_text(word: str, position: float, base_hex: str, flash_hex: str, flash_width: float) -> Text:
    """A palavra com um brilho varrendo a cor base (docs/17 §7)."""
    text = Text()
    for i, ch in enumerate(word):
        distance = abs(i - position)
        intensity = max(0.0, 1.0 - distance / flash_width)
        text.append(ch, style=f"bold {lerp_color(base_hex, flash_hex, intensity)}")
    return text
