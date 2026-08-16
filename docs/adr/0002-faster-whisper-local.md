# ADR-0002 · Transcrição local com faster-whisper em GPU

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** RNF-C01, RNF-C03, RNF-C04, RNF-P01

## Contexto

A transcrição pode rodar em serviço de nuvem (Deepgram, AssemblyAI, OpenAI) ou localmente. O serviço de nuvem é mais simples de integrar, tem boa qualidade em português e já traz diarização — mas cobra por hora de áudio e exige enviar a gravação da reunião para terceiros.

O projeto nasceu de um limite de uso atingido em ferramenta paga, e a máquina disponível tem GPU dedicada com 8 GB de memória de vídeo.

## Decisão

Transcrever **localmente** com `faster-whisper` (implementação do Whisper sobre CTranslate2), modelo `large-v3` quantizado em `int8_float16`, na GPU.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| API de nuvem | Custo por hora e envio do áudio para terceiro — contraria a motivação do projeto |
| Whisper de referência (PyTorch) | Consumo de memória maior e mais lento que CTranslate2 na mesma GPU |
| Modelo menor (`medium`, `small`) | Qualidade inferior em português; a GPU comporta o `large-v3` quantizado com folga |

## Consequências

**Positivas.** Custo recorrente zero. Nenhum áudio sai da máquina. Sem cota. Aproveita hardware ocioso.

**Negativas.** Amarra o sistema a uma máquina com GPU — não roda em qualquer lugar. `ctranslate2` com CUDA no Windows tem dependências de biblioteca que podem conflitar com outros pacotes do ambiente; este é o **maior risco técnico ainda não validado do projeto**. Não traz diarização pronta, embora o ADR-0001 torne isso irrelevante na captura ao vivo.

## Gatilho de reversão

Se o conflito de dependências se mostrar insolúvel mesmo com ambiente separado para o worker, ou se o projeto precisar rodar em máquina sem GPU. A camada de transcrição é isolada o suficiente para trocar por provedor de nuvem sem afetar o resto — ao custo de abandonar RNF-C01 e RNF-C04.
