"""Testes de cronista.client.banner (docs/17-identidade-visual-cli.md §7)."""

from __future__ import annotations

from rich.console import Console

from cronista.client import banner
from cronista.client.signal_bar import VOCE_COLOR


def test_render_banner_grande_em_terminal_largo() -> None:
    console = Console(force_terminal=True, width=banner.width() + 2)

    text = banner.render(console)

    assert text.plain.count("\n") > 0
    assert len(text.spans) > 0


def test_render_cai_pro_nome_simples_em_terminal_estreito() -> None:
    console = Console(force_terminal=True, width=banner.width() - 1)

    text = banner.render(console)

    assert text.plain == "cronista"
    assert text.style == f"bold {VOCE_COLOR}"


def test_render_sem_cor_quando_nao_e_terminal() -> None:
    console = Console(force_terminal=False)

    text = banner.render(console)

    assert text.plain == "cronista"
    assert text.style == ""


def test_render_banner_grande_nunca_escurece_alem_da_identidade() -> None:
    """docs/17 §6: já foi rejeitado gradiente indo pra tom muito escuro."""
    console = Console(force_terminal=True, width=banner.width() + 2)

    text = banner.render(console)

    for span in text.spans:
        hex_color = span.style.split()[-1].lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        # nenhum canal fica mais escuro que o ponto mais escuro fixado (_SHADE)
        shade = banner._SHADE.lstrip("#")
        sr, sg, sb = int(shade[0:2], 16), int(shade[2:4], 16), int(shade[4:6], 16)
        assert r >= sr - 1 and g >= sg - 1 and b >= sb - 1
