# ADR-0014 · Worker de transcrição em container com GPU

- **Status:** aceito
- **Data:** 2026-08-16
- **Requisitos relacionados:** RNF-C03, RNF-P01, RNF-P04
- **Complementa:** [ADR-0002](0002-faster-whisper-local.md)

## Contexto

O [ADR-0002](0002-faster-whisper-local.md) registrou o maior risco não resolvido do projeto: `ctranslate2` exige versões específicas de CUDA e cuDNN, o LangChain arrasta a própria árvore de dependências, e no mesmo ambiente Python os dois podem conflitar de forma difícil de diagnosticar. A mitigação prevista era ambiente virtual separado, o que ajuda mas não garante — as bibliotecas de CUDA são do sistema, não do ambiente Python.

Surgiu a sugestão de manter uma máquina virtual com uma imagem do Whisper sempre em execução. Ao examinar, a proposta continha duas ideias distintas:

1. **Manter o modelo sempre disponível.** Já contemplado — o worker é um processo longo que consome a fila. O ganho real é pequeno: carregar o modelo leva cerca de vinte segundos, num trabalho que dura minutos.
2. **Empacotar em imagem.** É a parte valiosa, mas pela razão de isolamento de dependência, não de disponibilidade.

**Máquina virtual não é viável nesta máquina.** Passthrough de GPU não está disponível no Hyper-V do Windows 11 cliente, e GPU de notebook agrava o caso. O WSL2 funciona por usar o caminho paravirtualizado da NVIDIA — verificado nesta máquina: `nvidia-smi` responde dentro do WSL, driver 610.88, 8188 MiB. O Docker já está presente; falta apenas o NVIDIA Container Toolkit.

### O orçamento de memória de vídeo

A restrição que governa o desenho. Os valores da primeira linha são **medidos nesta máquina**; os demais são estimativas a confirmar:

| Item | VRAM |
|---|---|
| **Linha de base do Windows** (desktop, navegador, editor) | **~1,5 a 2 GB · medido** |
| Total da RTX 4060 Laptop | 8,0 GB |
| **Disponível de fato** | **~6,3 GB** |
| Whisper `large-v3` int8_float16 | 4 a 5 GB (estimado) |
| Modelo de linguagem 8B quantizado | 5 a 6 GB (estimado) |

Duas conclusões:

1. **Transcrever e resumir são operações mutuamente exclusivas nesta máquina** — o que vale para container ou execução nativa, indiferentemente.
2. **A margem do Whisper é estreita.** Ele cabe nos ~6,3 GB, mas com pouca folga: abrir mais abas do navegador ou um jogo durante a transcrição pode estourar. O caminho de exceção FE-01 do UC-05 — nova tentativa com configuração de menor consumo — tende a ser exercitado com mais frequência do que o desenho inicial supunha, e não deve ser tratado como caso raro.

*A linha de base não é fixa: varia com o que está aberto. Medida em 2026-08-17 com uso típico de desktop, `nvidia-smi` reportou 1886 MiB ocupados e 27% de utilização em ociosidade.*

### Onde fica o áudio

Container em WSL2 lendo `%LOCALAPPDATA%` atravessa o compartilhamento 9P entre Windows e a máquina virtual, o que é sensivelmente mais lento que leitura local. A alternativa seria guardar o acervo dentro do WSL — mas isso apenas transfere a lentidão da **leitura** para a **escrita**, já que a captura é processo Windows.

A escolha decorre do [ADR-0012](0012-gravacao-em-disco-antes-da-api.md): gravar é irreversível, transcrever é repetível. Lentidão em leitura custa segundos num trabalho de minutos; lentidão em escrita durante a reunião pode custar áudio que não volta.

## Decisão

1. O **worker de transcrição roda em container** com acesso à GPU via WSL2 e NVIDIA Container Toolkit.
2. O modelo é **carregado sob demanda e liberado após período ocioso** — não permanece residente.
3. O **acervo de áudio permanece no Windows**, montado no container em modo leitura. A lentidão da fronteira é aceita conscientemente.
4. Transcrição e resumo **nunca executam simultaneamente**.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Processo nativo em ambiente virtual próprio | Não isola bibliotecas de CUDA, que são do sistema. Mantém o risco de pé |
| Máquina virtual completa | Não obtém a GPU nesta máquina |
| Container com modelo residente | Prende 4 a 5 GB dos 8 GB permanentemente, para economizar ~20 s de carregamento |
| Acervo dentro do WSL | Transfere a lentidão para a escrita, que é a operação irreversível |

## Consequências

**Positivas.** O maior risco técnico do projeto deixa de existir: as bibliotecas de CUDA ficam na imagem, e o ambiente da API nunca as enxerga. Ambiente reprodutível. A memória de vídeo fica livre quando não há transcrição em curso. Migrar a transcrição para outra máquina com GPU passa a ser trivial — o que conecta com a intenção de acesso a partir de outra máquina.

**Negativas.** Mais um componente de infraestrutura a operar. Requer o NVIDIA Container Toolkit instalado no WSL. Leitura de áudio atravessa a fronteira 9P, custando segundos por trilha. Os pesos do modelo (~3 GB) precisam de volume persistente. Carregamento sob demanda acrescenta cerca de vinte segundos ao início de cada transcrição.

## Gatilho de reversão

Se a fronteira 9P se mostrar lenta a ponto de comprometer RNF-P01 — transcrever mais rápido que o tempo real. **Isso é medição, não suposição**, e a medida está prevista em CT-16.

Nesse caso há dois caminhos antes de abandonar o container: copiar a trilha para dentro do WSL antes de processar, ou voltar ao processo nativo aceitando de novo o risco de dependência.

## Momento

Adotado antes de existir código. Depois da Fase 3 seria refatoração; agora é edição de documento.
