"""Orquestra a geração de resumo via LangChain (ADR-0005, docs/13-resumo.md).

Este módulo é o único lugar que conhece qual `BaseChatModel` usar --
trocar de provedor não deve exigir mudar nada fora daqui (RNF-S04).
Roda no processo da API, não no worker: o worker tem GPU só para o
Whisper, e VRAM não cabe os dois modelos ao mesmo tempo (docs/07-arquitetura.md §3).
"""

from __future__ import annotations

import re

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session

from cronista.core.config import Settings
from cronista.core.models import Meeting, Segment, Summary

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

_PROMPT_CONSOLIDACAO = """Você recebe abaixo resumos parciais do mesmo \
formato de quatro seções, cada um cobrindo um pedaço de uma reunião \
longa que foi dividida por não caber inteira numa única chamada -- na \
ordem em que aconteceram, com sobreposição entre pedaços consecutivos \
(o mesmo trecho pode aparecer resumido nos dois lados da divisão).

Consolide tudo num único resumo final, no mesmo formato -- \
Markdown com exatamente estas quatro seções, nesta ordem, cada uma com \
título em nível 2, exatamente "## " no início da linha (não "### ", \
não nenhum outro nível, mesmo que os pedaços recebidos abaixo estejam \
em outro nível): Pauta, Decisões, Pendências, Pontos em aberto.

Uma decisão ou pendência que aparece em dois pedaços por causa da \
sobreposição conta só uma vez. Preserve tudo que os pedaços, juntos, \
registraram -- nada pode se perder por causa da divisão. Se uma seção \
não tiver conteúdo, escreva-a mesmo assim, com o texto "Nenhum." abaixo \
do título -- nunca omita a seção. Nunca invente algo que não está em \
nenhum dos pedaços recebidos."""


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


def _texto_transcricao(segmentos: list[Segment]) -> str:
    return "\n".join(f"{s.speaker}: {s.text}" for s in segmentos)


def _tem_quatro_secoes(markdown: str) -> bool:
    # `in markdown` sozinho aceitava "### Pauta" como se fosse "## Pauta"
    # -- "## Pauta" é substring de "### Pauta" (achado testando de
    # verdade contra Ollama real, não presumido). Precisa do título
    # exatamente em nível 2, começando a linha.
    return all(
        re.search(rf"^## {re.escape(secao)}\b", markdown, re.MULTILINE) is not None
        for secao in _SECOES
    )


def _dividir_em_blocos(
    segmentos: list[Segment], limite_chars: int, sobreposicao: int
) -> list[list[Segment]]:
    """RF-17: divide em blocos que cabem em `limite_chars` (heurística de
    caracteres — docs/13-resumo.md §5), respeitando fronteira de
    segmento (nunca corta um no meio) e repetindo os últimos
    `sobreposicao` segmentos de um bloco como início do próximo, pra uma
    decisão perto da fronteira não se perder. Se um único segmento já
    excede `limite_chars` sozinho (raro -- fala de Whisper costuma ser
    curta), o bloco fica um pouco maior que o limite em vez de cortar a
    fala ao meio; truncar é o que RF-17 proíbe."""
    blocos: list[list[Segment]] = []
    atual: list[Segment] = []
    tamanho_atual = 0
    for segmento in segmentos:
        tamanho_linha = len(f"{segmento.speaker}: {segmento.text}\n")
        if atual and tamanho_atual + tamanho_linha > limite_chars:
            blocos.append(atual)
            atual = atual[-sobreposicao:] if sobreposicao else []
            tamanho_atual = sum(len(f"{s.speaker}: {s.text}\n") for s in atual)
        atual.append(segmento)
        tamanho_atual += tamanho_linha
    if atual:
        blocos.append(atual)
    return blocos


# CT-23, docs/13-resumo.md §7 / docs/11-cli.md §5: a mensagem tem que dizer
# de quem é a falha E o que fazer, não só nomear o provedor.
_DICA_PROVEDOR = {
    "ollama": "verifique se o Ollama está rodando (`ollama serve`) e se o "
    "modelo foi baixado (`ollama pull <modelo>`)",
    "anthropic": "verifique ANTHROPIC_API_KEY no .env e a conexão de rede",
}


def _invocar(modelo: BaseChatModel, prompt_sistema: str, texto: str, provider: str) -> str:
    try:
        # Exceção ampla de propósito: cada provedor levanta um tipo
        # diferente pra "não respondeu" (conexão recusada, timeout,
        # 401/503 do lado deles), e não vale a pena acoplar este módulo
        # aos detalhes internos de cada SDK só pra distinguir isso --
        # mesmo espírito de model_manager.is_out_of_memory, que também
        # aproxima em vez de casar com uma classe de exceção exata.
        resposta = modelo.invoke(
            [SystemMessage(content=prompt_sistema), HumanMessage(content=texto)]
        )
    except Exception as exc:
        dica = _DICA_PROVEDOR.get(provider, "verifique a configuração do provedor")
        raise ProviderUnavailable(f"{provider} não respondeu ({exc}) -- {dica}.") from exc
    return str(resposta.content)


def summarize(
    db: Session,
    meeting: Meeting,
    settings: Settings,
    provider: str | None = None,
) -> Summary:
    """Gera um novo resumo e persiste (RN-03: nunca sobrescreve, sempre
    insere). RF-18: `provider` escolhe o provedor por execução, sobrepondo
    o padrão de `settings.llm_provider`. RF-17: transcrição maior que
    `settings.summary_context_chars` divide em blocos com sobreposição,
    resume cada um e consolida — nunca trunca (docs/13-resumo.md §5)."""
    provider = provider or settings.llm_provider
    modelo = _modelo(settings, provider)
    segmentos = sorted(meeting.segments, key=lambda s: s.start_ms)
    transcricao = _texto_transcricao(segmentos)

    try:
        if len(transcricao) <= settings.summary_context_chars:
            markdown = _invocar(modelo, _PROMPT_SISTEMA, transcricao, provider)
        else:
            blocos = _dividir_em_blocos(
                segmentos, settings.summary_context_chars, settings.summary_block_overlap_segments
            )
            resumos_parciais = [
                _invocar(modelo, _PROMPT_SISTEMA, _texto_transcricao(bloco), provider)
                for bloco in blocos
            ]
            texto_consolidacao = "\n\n".join(
                f"--- Pedaço {i + 1} de {len(resumos_parciais)} ---\n{resumo}"
                for i, resumo in enumerate(resumos_parciais)
            )
            markdown = _invocar(modelo, _PROMPT_CONSOLIDACAO, texto_consolidacao, provider)
    except ProviderUnavailable:
        meeting.status = "summary_failed"
        db.commit()
        raise

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
