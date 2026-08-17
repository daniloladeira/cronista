"""Demonstracao descartavel de barra em gradiente truecolor, para decidir se
vale entrar no design do CLI. Nao faz parte do produto.

    python scripts/preview_gradient_bar.py

Ctrl+C para sair.
"""

from __future__ import annotations

import math
import shutil
import sys
import time

BLOCKS = "▁▂▃▄▅▆▇█"


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def color_for(t: float) -> tuple[int, int, int]:
    # 0.0 = verde, 0.5 = amarelo, 1.0 = vermelho — mesma logica de VU meter.
    if t < 0.5:
        k = t / 0.5
        return (int(lerp(40, 230, k)), 200, 60)
    k = (t - 0.5) / 0.5
    return (230, int(lerp(200, 40, k)), 60)


def render_bar(level: float, width: int) -> str:
    filled = int(level * width)
    out = []
    for i in range(width):
        t = i / max(width - 1, 1)
        r, g, b = color_for(t)
        char = BLOCKS[-1] if i < filled else BLOCKS[0]
        out.append(f"\x1b[38;2;{r};{g};{b}m{char}")
    out.append("\x1b[0m")
    return "".join(out)


def supports_truecolor() -> bool:
    colorterm = __import__("os").environ.get("COLORTERM", "")
    return colorterm in ("truecolor", "24bit")


def main() -> int:
    if not sys.stdout.isatty():
        print("[AVISO] Saida nao e um terminal interativo; efeito nao aparece redirecionado.")
    if not supports_truecolor():
        print("[AVISO] COLORTERM nao indica truecolor. Pode aparecer em blocos de cor, nao gradiente liso.")
        print("        (Windows Terminal moderno costuma suportar; cmd.exe classico, nao.)")

    width = min(shutil.get_terminal_size().columns - 10, 60)
    print("\nSimulando o indicador de sinal do RF-05. Ctrl+C para sair.\n")

    t = 0.0
    try:
        while True:
            level = (math.sin(t) + 1) / 2  # 0..1, so pra ter algo se mexendo
            sys.stdout.write("\r  " + render_bar(level, width) + "  ")
            sys.stdout.flush()
            t += 0.15
            time.sleep(0.075)  # mesmo intervalo do artigo do GitHub: ~13fps
    except KeyboardInterrupt:
        print("\n\nEncerrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
