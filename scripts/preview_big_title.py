"""Preview: 'CRONISTA' em letras de bloco, fonte de matriz de LED 5x7.
Responde a pergunta 'da pra aumentar a letra' -- terminal nao faz isso,
letra grande e sempre desenhada em blocos, tipo o banner do torlink.
Descartavel, so para decidir antes de virar o banner real (docs/17 secao 7).

    python scripts/preview_big_title.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.text import Text

from cronista.client.signal_bar import VOCE_COLOR

console = Console()

# Fonte de matriz de LED 5x7, so as letras de "CRONISTA".
_FONT: dict[str, list[str]] = {
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
}

BLOCK = "██"  # cada "pixel" ocupa 2 colunas, fica mais quadrado
GAP = "  "  # espaco entre letras


def render_big_text(word: str, color: str) -> Text:
    rows = ["" for _ in range(7)]
    for letter in word.upper():
        pattern = _FONT.get(letter, _FONT[" "])
        for row_idx, row in enumerate(pattern):
            rows[row_idx] += "".join(BLOCK if ch == "#" else "  " for ch in row) + GAP

    text = Text()
    for row in rows:
        text.append(row.rstrip() + "\n", style=color)
    return text


def main() -> int:
    console.print()
    console.print(render_big_text("CRONISTA", VOCE_COLOR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
