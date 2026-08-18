"""Interpolação de cor hex, compartilhada entre signal_bar.py (shimmer do
cabeçalho) e banner.py (degradê 2D da abertura, docs/17-identidade-visual-cli.md §7).
"""

from __future__ import annotations


def lerp_color(base_hex: str, target_hex: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(base_hex[1:3], 16), int(base_hex[3:5], 16), int(base_hex[5:7], 16)
    r2, g2, b2 = int(target_hex[1:3], 16), int(target_hex[3:5], 16), int(target_hex[5:7], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"
