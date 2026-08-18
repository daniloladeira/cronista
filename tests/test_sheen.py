"""Testes de cronista.client.sheen -- matemática pura, sem consumidor
ainda (ver docstring do módulo)."""

from __future__ import annotations

import math

from cronista.client import sheen


def test_sheen_period_soma_largura_raio_e_lacuna() -> None:
    assert sheen.sheen_period(20) == math.ceil(20 + sheen.SHEEN_RADIUS * 2) + sheen.SHEEN_GAP


def test_sheen_center_avanca_uma_velocidade_por_tick() -> None:
    period = sheen.sheen_period(20)

    c0 = sheen.sheen_center(0, period)
    c1 = sheen.sheen_center(1, period)

    assert abs((c1 - c0) - sheen.SHEEN_SPEED) < 1e-9


def test_sheen_loop_ticks_aproxima_periodo_dividido_pela_velocidade() -> None:
    period = sheen.sheen_period(20)

    loop_ticks = sheen.sheen_loop_ticks(period)

    assert abs(loop_ticks - period / sheen.SHEEN_SPEED) <= 0.5


def test_sheen_intensity_no_centro_e_o_pico() -> None:
    assert sheen.sheen_intensity(5, 5.0) == sheen.SHEEN_MAX


def test_sheen_intensity_zero_fora_do_raio() -> None:
    assert sheen.sheen_intensity(0, 10.0) == 0.0


def test_sheen_intensity_e_simetrica_ao_redor_do_centro() -> None:
    center = 10.0
    assert sheen.sheen_intensity(8, center) == sheen.sheen_intensity(12, center)


def test_sheen_intensity_nunca_passa_do_maximo() -> None:
    for i in range(30):
        assert 0.0 <= sheen.sheen_intensity(i, 15.0) <= sheen.SHEEN_MAX
