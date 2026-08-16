# ADR-0001 · Captura local em duas trilhas, sem diarização

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** RF-02, RF-11, RNF-C02

## Contexto

O sistema precisa saber quem falou cada trecho. A abordagem convencional é gravar tudo numa trilha e aplicar diarização — separação de falantes por análise do sinal. Diarização custa processamento, exige modelo adicional e erra com frequência em áudio de reunião, onde há sobreposição de fala e qualidade de microfone variável.

Existe uma alternativa disponível no Windows: a WASAPI expõe captura de *loopback*, isto é, do áudio que está saindo pela placa de som. Isso permite gravar separadamente o que o usuário fala (microfone) e o que os outros falam (saída).

## Decisão

Gravar **duas trilhas independentes** — microfone e loopback da saída — a 16 kHz mono, e atribuir o falante pela **origem do sinal**, não por análise de conteúdo. Não usar diarização na captura ao vivo.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Trilha única + diarização (pyannote) | Custo de processamento, modelo extra, e erro de atribuição em sobreposição de fala |
| Bot participante da chamada | Frágil a mudanças de interface das plataformas, visível aos participantes |
| Microfone apontado para a caixa de som | Qualidade sofrível, capta ruído ambiente |

## Consequências

**Positivas.** A separação "usuário × demais" é exata por construção, não estimada — não há como errar. Custo zero de processamento. Funciona com qualquer plataforma de reunião, inclusive as sem API.

**Negativas.** Distingue apenas dois grupos: não identifica cada participante individualmente dentro de `outros`. Depende de o sistema operacional expor loopback, o que amarra o projeto ao Windows na versão atual. Dobra o volume de áudio em disco e o trabalho de transcrição.

## Gatilho de reversão

Se for necessário identificar participantes **nominalmente** dentro da trilha `outros`, ou se o projeto precisar rodar onde não haja loopback disponível. Nesses casos, diarização volta à mesa — mas como acréscimo à separação por trilha, não como substituição.
