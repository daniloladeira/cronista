"""Testes de cronista/client/naming.py."""

from __future__ import annotations

from datetime import datetime

from cronista.client.naming import make_audio_dir, slugify


def test_slugify_remove_acento_e_espaco():
    assert slugify("Reunião Comercial") == "reuniao-comercial"


def test_slugify_titulo_vazio_usa_fallback():
    assert slugify("") == "reuniao"
    assert slugify("!!!") == "reuniao"


def test_slugify_trunca_titulo_muito_longo():
    titulo = "a" * 100
    assert len(slugify(titulo)) <= 50


def test_slugify_colapsa_separadores_repetidos():
    assert slugify("Reunião   com --- Cliente") == "reuniao-com-cliente"


def test_make_audio_dir_formato_esperado():
    started_at = datetime(2026, 8, 12, 14, 30)
    assert make_audio_dir("Reunião Comercial", started_at) == "2026-08-12_1430_reuniao-comercial"


def test_make_audio_dir_sem_titulo_usa_fallback():
    started_at = datetime(2026, 8, 17, 9, 5)
    assert make_audio_dir("", started_at) == "2026-08-17_0905_reuniao"
