"""Orquestra a geração de resumo via LangChain (ADR-0005, docs/13-resumo.md).

Este módulo é o único lugar que conhece qual `BaseChatModel` usar --
trocar de provedor não deve exigir mudar nada fora daqui (RNF-S04).
Roda no processo da API, não no worker: o worker tem GPU só para o
Whisper, e VRAM não cabe os dois modelos ao mesmo tempo (docs/07-arquitetura.md §3).
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session

from cronista.core.config import Settings
from cronista.core.models import Meeting, Summary

PROMPT_VERSION = "v3"

_SECOES = ("Pauta", "Decisões", "Pendências", "Pontos em aberto")

_PROMPT_SISTEMA = """Você resume reuniões em português do Brasil. A saída é \
Markdown com exatamente estas quatro seções, nesta ordem, cada uma com o \
título em nível 2 (##):

## Pauta
Assuntos tratados, na ordem em que apareceram. Só os temas discutidos -- \
não repita aqui decisões nem pendências, que têm seções próprias.

## Decisões
Algo que o grupo resolveu ou concordou, mas que **não** gera uma ação \
futura de alguém específico -- por exemplo, escolher uma opção entre \
várias, aprovar um formato, encerrar uma discussão. Se a frase tem \
"eu vou fazer X" ou "fulano fica responsável por X", isso é Pendência, \
não Decisão -- não repita aqui.

## Pendências
Toda ação que alguém assumiu de fazer depois da reunião -- **procure \
isso primeiro**, antes de decidir o que vai em Decisões. Frases como \
"eu fico responsável", "eu vou fazer", "fico com isso", "fulano ficou \
de fazer X" são sempre Pendência, nunca Decisão, mesmo que soem como \
uma decisão do grupo. Cada uma precisa indicar o responsável: quando \
alguém fala na primeira pessoa, o responsável é quem está falando \
naquele trecho da transcrição -- nunca escreva "não ficou claro quem \
é" nesse caso, só quando a transcrição de fato não permitir identificar \
ninguém.

Exemplo (não faz parte da reunião real, é só pra ilustrar a diferença):
transcrição: "voce: fechado, então já era a decisão de manter Postgres.
outros: combinado, e eu fico responsável por atualizar o schema até
quinta." --
Decisões: manter Postgres como banco.
Pendências: outros -- atualizar o schema até quinta-feira.

## Pontos em aberto
O que foi levantado e não chegou a se resolver.

Se uma seção não tiver conteúdo, escreva-a mesmo assim, com o texto \
"Nenhum." abaixo do título -- nunca omita a seção.

Nunca invente uma decisão, pendência ou fala que não está na transcrição. \
Um resumo errado é pior que nenhum resumo."""


class ProviderUnavailable(RuntimeError):
    """O provedor de LLM não respondeu (docs/13-resumo.md §7) -- a rota
    converte isso em 503. Nunca persiste resumo parcial."""


class RespostaMalformada(RuntimeError):
    """A resposta não trouxe as quatro seções esperadas -- guarda a
    resposta bruta pra diagnóstico, mas não persiste como Summary
    (docs/13-resumo.md §7: nunca gravar resumo malformado como válido)."""

    def __init__(self, resposta_bruta: str) -> None:
        super().__init__("resposta do modelo não trouxe as quatro seções esperadas")
        self.resposta_bruta = resposta_bruta


def _nome_modelo(settings: Settings, provider: str) -> str:
    if provider == "ollama":
        return settings.ollama_model
    if provider == "anthropic":
        return settings.anthropic_model
    raise ValueError(f"provedor de LLM desconhecido: {provider!r}")


def _modelo(settings: Settings, provider: str) -> BaseChatModel:
    if provider == "ollama":
        return ChatOllama(base_url=settings.ollama_base_url, model=settings.ollama_model)
    if provider == "anthropic":
        return ChatAnthropic(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
    raise ValueError(f"provedor de LLM desconhecido: {provider!r}")


def _texto_transcricao(meeting: Meeting) -> str:
    segmentos = sorted(meeting.segments, key=lambda s: s.start_ms)
    return "\n".join(f"{s.speaker}: {s.text}" for s in segmentos)


def _tem_quatro_secoes(markdown: str) -> bool:
    return all(f"## {secao}" in markdown for secao in _SECOES)


def summarize(
    db: Session,
    meeting: Meeting,
    settings: Settings,
    provider: str | None = None,
) -> Summary:
    """Gera um novo resumo e persiste (RN-03: nunca sobrescreve, sempre
    insere). RF-18: `provider` escolhe o provedor por execução, sobrepondo
    o padrão de `settings.llm_provider`."""
    provider = provider or settings.llm_provider
    modelo = _modelo(settings, provider)
    transcricao = _texto_transcricao(meeting)

    try:
        # Exceção ampla de propósito: cada provedor levanta um tipo
        # diferente pra "não respondeu" (conexão recusada, timeout,
        # 401/503 do lado deles), e não vale a pena acoplar este módulo
        # aos detalhes internos de cada SDK só pra distinguir isso --
        # mesmo espírito de model_manager.is_out_of_memory, que também
        # aproxima em vez de casar com uma classe de exceção exata.
        resposta = modelo.invoke(
            [SystemMessage(content=_PROMPT_SISTEMA), HumanMessage(content=transcricao)]
        )
    except Exception as exc:
        meeting.status = "summary_failed"
        db.commit()
        raise ProviderUnavailable(f"{provider} não respondeu: {exc}") from exc

    markdown = str(resposta.content)
    if not _tem_quatro_secoes(markdown):
        meeting.status = "summary_failed"
        db.commit()
        raise RespostaMalformada(markdown)

    summary = Summary(
        meeting_id=meeting.id,
        provider=provider,
        model=_nome_modelo(settings, provider),
        prompt_version=PROMPT_VERSION,
        markdown=markdown,
    )
    db.add(summary)
    meeting.status = "summarized"
    db.commit()
    db.refresh(summary)
    return summary
