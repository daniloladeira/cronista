"""Testes de cronista.api.summarize contra Postgres real (mesma fixture
db_session da API, docs/14-plano-de-testes.md §7). O BaseChatModel é
mockado -- a validação com Ollama de verdade fica pra etapa 3
(docs/13-resumo.md §3: modelo se escolhe medindo, não antes)."""

from __future__ import annotations

import re
import uuid
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


class _ModeloSequencial:
    """Devolve uma resposta diferente a cada chamada, na ordem dada --
    usa pra distinguir as chamadas de bloco da chamada de consolidação
    (RF-17). Falha na N-ésima chamada se `falha_na_chamada` for dado."""

    def __init__(self, respostas: list[str], falha_na_chamada: int | None = None) -> None:
        self._respostas = list(respostas)
        self._falha_na_chamada = falha_na_chamada
        self.chamadas: list[list[object]] = []

    def invoke(self, mensagens: list[object]) -> _RespostaFalsa:
        self.chamadas.append(mensagens)
        if self._falha_na_chamada == len(self.chamadas):
            raise RuntimeError("connection refused")
        return _RespostaFalsa(self._respostas[len(self.chamadas) - 1])


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


@pytest.mark.parametrize(
    "transformacao",
    [
        lambda s: re.sub(r"^## ", "### ", s, flags=re.MULTILINE),  # nível 3 puro
        lambda s: re.sub(r"^## ", "### ## ", s, flags=re.MULTILINE),  # "###" colado na frente
        lambda s: re.sub(r"^## (.+)$", r"**## \1**", s, flags=re.MULTILINE),  # negrito em volta
    ],
    ids=["nivel_tres", "cabecalho_duplicado", "negrito"],
)
def test_summarize_normaliza_variantes_de_titulo_e_aceita(
    db_session: Session, monkeypatch, transformacao
) -> None:
    # Três variantes de formatação achadas testando contra reunião real
    # no mesmo dia (2026-08-22) -- o modelo varia o nível de cabeçalho e
    # o negrito mesmo quando o conteúdo está certo. Normaliza em vez de
    # rejeitar (docs/13-resumo.md §5).
    meeting = _com_segmentos(db_session, _meeting())
    resposta_com_ruido = transformacao(_RESUMO_VALIDO)
    modelo = _ModeloFalso(resposta_com_ruido)
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: modelo)

    resultado = summarize.summarize(db_session, meeting, _settings())

    assert resultado.markdown == _RESUMO_VALIDO


def test_summarize_secao_realmente_ausente_continua_malformada(
    db_session: Session, monkeypatch
) -> None:
    # A tolerância de formatação não vira tolerância de conteúdo -- se
    # uma seção não aparece de jeito nenhum (nem com título variante),
    # continua malformado (docs/13-resumo.md §7).
    meeting = _com_segmentos(db_session, _meeting())
    resposta_incompleta = _RESUMO_VALIDO.split("## Pontos em aberto")[0]  # falta a última seção
    modelo = _ModeloFalso(resposta_incompleta)
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: modelo)

    with pytest.raises(summarize.RespostaMalformada):
        summarize.summarize(db_session, meeting, _settings())


def test_summarize_provedor_indisponivel_marca_falha_sem_persistir(
    db_session: Session, monkeypatch
) -> None:
    meeting = _com_segmentos(db_session, _meeting())
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: _ModeloQueFalha())

    with pytest.raises(summarize.ProviderUnavailable) as exc_info:
        summarize.summarize(db_session, meeting, _settings())

    assert meeting.status == "summary_failed"
    assert meeting.summaries == []
    # CT-23, docs/13 §7: mensagem diz de quem é a falha e o que fazer,
    # não só que "não respondeu".
    assert "ollama serve" in str(exc_info.value)


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


def _segmentos_sinteticos(quantidade: int) -> list[Segment]:
    meeting_id = uuid.uuid4()
    return [
        Segment(
            meeting_id=meeting_id,
            speaker="voce" if i % 2 == 0 else "outros",
            start_ms=i * 1000,
            end_ms=(i + 1) * 1000,
            text=f"fala numero {i} com algum texto de enchimento",
        )
        for i in range(quantidade)
    ]


def test_dividir_em_blocos_nenhum_segmento_se_perde() -> None:
    segmentos = _segmentos_sinteticos(10)

    blocos = summarize._dividir_em_blocos(segmentos, limite_chars=80, sobreposicao=2)

    assert len(blocos) > 1  # o limite força mais de um bloco
    ids_nos_blocos = {s.start_ms for bloco in blocos for s in bloco}
    assert ids_nos_blocos == {s.start_ms for s in segmentos}


def test_dividir_em_blocos_mantem_ordem_cronologica_dentro_do_bloco() -> None:
    segmentos = _segmentos_sinteticos(10)

    blocos = summarize._dividir_em_blocos(segmentos, limite_chars=80, sobreposicao=2)

    for bloco in blocos:
        assert [s.start_ms for s in bloco] == sorted(s.start_ms for s in bloco)


def test_dividir_em_blocos_sobrepoe_segmentos_entre_blocos_consecutivos() -> None:
    segmentos = _segmentos_sinteticos(10)

    blocos = summarize._dividir_em_blocos(segmentos, limite_chars=80, sobreposicao=2)

    for anterior, seguinte in zip(blocos, blocos[1:]):
        # o bloco anterior pode ter menos de `sobreposicao` segmentos (ex.:
        # o primeiro bloco) -- a sobreposição real é limitada pelo que existe.
        tamanho_sobreposicao = min(2, len(anterior))
        assert anterior[-tamanho_sobreposicao:] == seguinte[:tamanho_sobreposicao]


def test_dividir_em_blocos_transcricao_pequena_gera_um_bloco_so() -> None:
    segmentos = _segmentos_sinteticos(3)

    blocos = summarize._dividir_em_blocos(segmentos, limite_chars=10_000, sobreposicao=2)

    assert len(blocos) == 1
    assert blocos[0] == segmentos


def test_summarize_transcricao_grande_divide_resume_blocos_e_consolida(
    db_session: Session, monkeypatch
) -> None:
    meeting = _meeting()
    db_session.add(meeting)
    db_session.flush()
    # 4 segmentos, cada linha ~35 chars -- limite de 40 força 1 segmento
    # por bloco (sem sobreposição, pra manter a contagem de blocos previsível).
    for i in range(4):
        db_session.add(
            Segment(
                meeting_id=meeting.id,
                speaker="voce",
                start_ms=i * 1000,
                end_ms=(i + 1) * 1000,
                text=f"fala numero {i} com enchimento",
            )
        )
    db_session.commit()
    db_session.refresh(meeting)

    resumos_de_bloco = [f"## Pauta\nbloco {i}\n\n## Decisões\nNenhuma.\n\n## Pendências\nNenhum.\n\n## Pontos em aberto\nNenhum." for i in range(4)]
    resumo_final = _RESUMO_VALIDO
    modelo = _ModeloSequencial([*resumos_de_bloco, resumo_final])
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: modelo)

    resultado = summarize.summarize(
        db_session, meeting, _settings(summary_context_chars=40, summary_block_overlap_segments=0)
    )

    assert len(modelo.chamadas) == 5  # 4 blocos (1 segmento cada) + consolidação
    for chamada in modelo.chamadas[:4]:
        assert chamada[0].content == summarize._PROMPT_SISTEMA
    ultima_chamada = modelo.chamadas[-1]
    assert ultima_chamada[0].content == summarize._PROMPT_CONSOLIDACAO
    for resumo_de_bloco in resumos_de_bloco:
        assert resumo_de_bloco in ultima_chamada[1].content  # consolidação recebeu todos os blocos
    assert resultado.markdown == resumo_final  # markdown final é o da consolidação


def test_summarize_bloco_com_falha_marca_summary_failed_sem_persistir(
    db_session: Session, monkeypatch
) -> None:
    meeting = _com_segmentos(db_session, _meeting())
    modelo = _ModeloSequencial(["algo"], falha_na_chamada=1)
    monkeypatch.setattr(summarize, "_modelo", lambda settings, provider: modelo)

    with pytest.raises(summarize.ProviderUnavailable):
        summarize.summarize(db_session, meeting, _settings(summary_context_chars=5))

    assert meeting.status == "summary_failed"
    assert meeting.summaries == []
