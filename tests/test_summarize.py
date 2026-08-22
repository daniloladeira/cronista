"""Testes de cronista.api.summarize contra Postgres real (mesma fixture
db_session da API, docs/14-plano-de-testes.md §7). O BaseChatModel é
mockado -- a validação com Ollama de verdade fica pra etapa 3
(docs/13-resumo.md §3: modelo se escolhe medindo, não antes)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from cronista.api import summarize
from cronista.core.config import Settings
from cronista.core.models import Meeting, Segment


class _RespostaFalsa:
    def __init__(self, content: str) -> None:
        self.content = content


class _ModeloFalso:
    """Substitui o BaseChatModel real -- guarda as mensagens recebidas
    pra inspeção, devolve o texto configurado."""

    def __init__(self, content: str) -> None:
        self._content = content
        self.mensagens_recebidas: list[object] | None = None

    def invoke(self, mensagens: list[object]) -> _RespostaFalsa:
        self.mensagens_recebidas = mensagens
        return _RespostaFalsa(self._content)


class _ModeloQueFalha:
    def invoke(self, mensagens: list[object]) -> _RespostaFalsa:
        raise RuntimeError("connection refused")


_RESUMO_VALIDO = """## Pauta
Assunto único.

## Decisões
Nenhuma.

## Pendências
Nenhum.

## Pontos em aberto
Nenhum."""


def _settings(**overrides: object) -> Settings:
    defaults = dict(
        database_url="unused-aqui-a-sessao-de-teste-ja-vem-pronta",
        auth_username="teste",
        auth_password_hash="hash-de-teste",
        jwt_secret="segredo-de-teste",
        data_root="/tmp/nao-usado-neste-teste",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _meeting(**overrides: object) -> Meeting:
    defaults = dict(
        title="Reunião de teste",
        source="capture",
        host="maquina-de-teste",
        audio_dir="2026-08-21_teste",
        expected_tracks=2,
        status="transcribed",
        started_at=datetime(2026, 8, 21, 14, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return Meeting(**defaults)


def _com_segmentos(db_session: Session, meeting: Meeting) -> Meeting:
    db_session.add(meeting)
    db_session.flush()
    db_session.add_all(
        [
            Segment(meeting_id=meeting.id, speaker="outros", start_ms=0, end_ms=2000, text="Oi"),
            Segment(
                meeting_id=meeting.id,
                speaker="voce",
                start_ms=2000,
                end_ms=4000,
                text="Tudo certo?",
            ),
        ]
    )
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


def test_summarize_com_sucesso_persiste_e_muda_status(db_session: Session, monkeypatch) -> None:
    meeting = _com_segmentos(db_session, _meeting())
    modelo = _ModeloFalso(_RESUMO_VALIDO)
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: modelo)

    resultado = summarize.summarize(db_session, meeting, _settings(ollama_model="teste-1b"))

    assert resultado.markdown == _RESUMO_VALIDO
    assert resultado.provider == "ollama"
    assert resultado.model == "teste-1b"
    assert resultado.prompt_version == summarize.PROMPT_VERSION
    assert meeting.status == "summarized"


def test_summarize_monta_transcricao_ordenada_por_falante_e_instante(
    db_session: Session, monkeypatch
) -> None:
    meeting = _com_segmentos(db_session, _meeting())
    modelo = _ModeloFalso(_RESUMO_VALIDO)
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: modelo)

    summarize.summarize(db_session, meeting, _settings())

    texto_enviado = modelo.mensagens_recebidas[1].content
    assert texto_enviado == "outros: Oi\nvoce: Tudo certo?"


def test_summarize_nunca_sobrescreve_gera_novo_registro(db_session: Session, monkeypatch) -> None:
    meeting = _com_segmentos(db_session, _meeting())
    modelo = _ModeloFalso(_RESUMO_VALIDO)
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: modelo)

    primeiro = summarize.summarize(db_session, meeting, _settings())
    segundo = summarize.summarize(db_session, meeting, _settings())

    assert primeiro.id != segundo.id
    assert len(meeting.summaries) == 2


def test_summarize_resposta_malformada_nao_persiste_e_marca_falha(
    db_session: Session, monkeypatch
) -> None:
    meeting = _com_segmentos(db_session, _meeting())
    modelo = _ModeloFalso("isso não é markdown com as quatro seções")
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: modelo)

    with pytest.raises(summarize.RespostaMalformada) as exc_info:
        summarize.summarize(db_session, meeting, _settings())

    assert exc_info.value.resposta_bruta == "isso não é markdown com as quatro seções"
    assert meeting.status == "summary_failed"
    assert meeting.summaries == []


def test_summarize_provedor_indisponivel_marca_falha_sem_persistir(
    db_session: Session, monkeypatch
) -> None:
    meeting = _com_segmentos(db_session, _meeting())
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: _ModeloQueFalha())

    with pytest.raises(summarize.ProviderUnavailable):
        summarize.summarize(db_session, meeting, _settings())

    assert meeting.status == "summary_failed"
    assert meeting.summaries == []


def test_summarize_aceita_provider_explicito_sobrepondo_configuracao(
    db_session: Session, monkeypatch
) -> None:
    meeting = _com_segmentos(db_session, _meeting())
    modelo = _ModeloFalso(_RESUMO_VALIDO)
    provedores_pedidos = []
    monkeypatch.setattr(
        summarize,
        "_modelo",
        lambda settings, provider: (provedores_pedidos.append(provider), modelo)[1],
    )

    resultado = summarize.summarize(
        db_session, meeting, _settings(anthropic_model="claude-teste"), provider="anthropic"
    )

    assert provedores_pedidos == ["anthropic"]
    assert resultado.provider == "anthropic"
    assert resultado.model == "claude-teste"


@pytest.mark.parametrize("status", ["transcribed", "summarized", "summary_failed"])
def test_is_summarizable_cobre_os_tres_estados_elegiveis(status: str) -> None:
    assert _meeting(status=status).is_summarizable()


@pytest.mark.parametrize("status", ["registering", "recorded", "transcribing", "transcription_failed"])
def test_is_summarizable_recusa_estados_nao_elegiveis(status: str) -> None:
    assert not _meeting(status=status).is_summarizable()
