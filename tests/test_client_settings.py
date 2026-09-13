"""Testes de cronista/client/settings.py -- substitui ClientSettings
(pydantic) do lado do cliente por medida de latência (ADR-0017), precisa
cobrir a mesma precedência que a lib garantia sozinha antes."""

from __future__ import annotations

import pytest

from cronista.client import settings as settings_module
from cronista.client.settings import ClientSettings


def _escreve_env(tmp_path, conteudo: str):
    caminho = tmp_path / ".env"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def test_le_do_arquivo_env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_module, "_ENV_FILE", _escreve_env(tmp_path, "API_BASE_URL=http://a\nDATA_ROOT=/dados\n"))
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("DATA_ROOT", raising=False)

    s = ClientSettings()

    assert s.api_base_url == "http://a"
    assert s.data_root == "/dados"


def test_variavel_de_ambiente_tem_precedencia_sobre_arquivo(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_module, "_ENV_FILE", _escreve_env(tmp_path, "API_BASE_URL=http://do-arquivo\nDATA_ROOT=/dados\n"))
    monkeypatch.setenv("API_BASE_URL", "http://da-variavel")

    s = ClientSettings()

    assert s.api_base_url == "http://da-variavel"


def test_ignora_linha_em_branco_e_comentario(tmp_path, monkeypatch):
    monkeypatch.setattr(
        settings_module,
        "_ENV_FILE",
        _escreve_env(tmp_path, "\n# comentário\nAPI_BASE_URL=http://a\n\nDATA_ROOT=/dados\n"),
    )
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("DATA_ROOT", raising=False)

    s = ClientSettings()

    assert s.api_base_url == "http://a"


def test_campo_ausente_em_variavel_e_arquivo_e_erro_claro(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_module, "_ENV_FILE", tmp_path / ".env")  # arquivo nem existe
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("DATA_ROOT", raising=False)

    with pytest.raises(ValueError, match="API_BASE_URL"):
        ClientSettings()
