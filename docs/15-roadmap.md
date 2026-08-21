# Roadmap

> **Versão:** 1.1 · **Última atualização:** 2026-08-17

## 1. Ordem e critério

Nove fases. Cada uma entrega algo utilizável e só está concluída quando seus casos de teste passam, **inclusive os de exceção** ([14-plano-de-testes.md](14-plano-de-testes.md) §8).

| Fase | Entrega | Casos de uso | Testes |
|---|---|---|---|
| 1 | Infraestrutura e autenticação | UC-01 | CT-01 a CT-04, CT-38 a CT-40 |
| 2 | Captura e envio | UC-02, UC-03, UC-10, UC-11 | CT-05 a CT-11, CT-33 a CT-35 |
| 3 | Transcrição | UC-05 | CT-16 a CT-20, CT-36 |
| 4 | Resumo | UC-06 | CT-21 a CT-24, CT-37 |
| 5 | Consulta e busca | UC-07, UC-08 | CT-25 a CT-29 |
| 6 | Importação de arquivo | UC-04 | CT-12 a CT-15 |
| 7 | Retenção e exclusão | UC-09 | CT-30 a CT-32 |
| 8 | Interface desktop | n/d | n/d |
| 9 | Leitura remota | n/d | n/d |

## 2. Detalhamento

### Fase 1 · Infraestrutura e autenticação

PostgreSQL em container, migração inicial com as quatro tabelas, FastAPI no ar, login com JWT.

**Pronto quando:** `docker compose up -d` sobe o banco, `alembic upgrade head` cria o esquema, `cronista login` devolve token, e um endpoint protegido recusa requisição sem token.

**Concluída em 2026-08-17.** Os quatro critérios verificados contra ambiente real: Postgres em container (com a porta remapeada para 5433, já que a 5432 pertence a outra instância nativa desta máquina), migração aplicada com as quatro tabelas mais `alembic_version`, `cronista login` devolvendo tokens salvos em `%LOCALAPPDATA%\cronista\auth.json`, e a rejeição sem token coberta por `tests/test_auth.py` (CT-01 a CT-04, CT-40).

**Fase de infraestrutura pura, sem funcionalidade visível.** É o custo de ter escolhido a API como centro do sistema ([ADR-0010](adr/0010-api-como-centro.md)), e é melhor pagá-lo de uma vez do que parcelado.

### Fase 2 · Captura e envio

O coração do sistema. Captura WASAPI em duas trilhas, escrita incremental em disco, registro na API, índice local de pendências e reconciliação.

**Pronto quando:** uma reunião real é gravada em dois WAV corretos, aparece no banco, e **CT-08 passa**: a API derrubada no meio da gravação não custa o áudio.

**Risco já eliminado:** a captura de loopback foi verificada nesta máquina antes do planejamento. A biblioteca enxerga a saída padrão e gravou 1 segundo real a 16 kHz mono.

**Concluída em 2026-08-17.** `cronista rec`/`devices` gravando de verdade nesta máquina, com pausar/retomar (RF-31) sem truncar o WAV; registro na API com renovação silenciosa de token; `pending.json` e `cronista sync` cobrindo API indisponível (CT-33 a CT-35); CT-08 verificado tanto com hardware real (derrubando o container no meio de uma gravação) quanto em teste automatizado de ponta a ponta (`tests/test_ct08_api_indisponivel.py`). CT-05, CT-06, CT-07, CT-09 a CT-11 e CT-42 também cobertos por teste. `tests/test_capture_pause.py`, `test_capture_record.py`, `test_reconciliation.py` e `test_ct08_api_indisponivel.py` simulam hardware e falha de API sem depender de microfone real — o que exigiu dispositivo real foi verificado à parte, não fica preso à suíte.

### Fase 3 · Transcrição

Worker em processo separado, consumindo a fila do banco. Detecção de fala, transcrição por trilha, mesclagem cronológica.

**Pronto quando:** uma reunião de 1 hora é transcrita em menos de 1 hora, com falantes corretos, e a linha de base de WER está medida.

**Pré-requisito de ambiente: resolvido em 2026-08-17.** NVIDIA Container Toolkit 1.20.0 instalado no WSL e verificado: `docker run --rm --gpus all ubuntu nvidia-smi` enxerga a RTX 4060 de dentro do container.

**Restrição medida na mesma verificação:** o desktop do Windows consome ~1,5 a 2 GB de VRAM, deixando ~6,3 GB reais dos 8 GB nominais. O Whisper cabe com pouca folga, ver [ADR-0014](adr/0014-worker-em-container-com-gpu.md).

**O maior risco do projeto foi endereçado antes da implementação.** `ctranslate2` com CUDA convivendo com as dependências de LangChain deixou de ser problema com o worker em container ([ADR-0014](adr/0014-worker-em-container-com-gpu.md)): as bibliotecas de CUDA ficam na imagem e o ambiente da API nunca as vê.

**O risco que sobra é outro, e é medível:** o container lê o áudio atravessando a fronteira 9P entre WSL e Windows, o que é mais lento que leitura local. Se comprometer RNF-P01, a saída é copiar a trilha para dentro do WSL antes de processar. **CT-16 responde isso com número, não com suposição.**

**CT-16 medido em 2026-08-21, com reunião real: passou com folga larga.** Reunião de 59min39s (duas trilhas, `voce` e `outros`), gravada e reprocessada pelo pipeline completo (`cronista rec` → API → fila → `cronista-worker` em container com GPU). Do momento em que o worker reivindicou a reunião (checagem do modelo no Hugging Face) até o modelo voltar a ficar ocioso: **~2min26s**, medido pelos timestamps do log do worker (claim às 12:02:34, última atividade do modelo entre 12:04:58 e 12:05:04, inferido do log de descarregamento por ociosidade 300s depois). Ou seja, ~24x mais rápido que tempo real — a fronteira 9P WSL↔Windows não se mostrou um gargalo relevante nessa medição; a cópia pro WSL cogitada como saída de contingência não foi necessária. 1069 segmentos persistidos (924 `outros`, 145 `voce`), cobrindo a reunião inteira (`max(end_ms)` bate com a duração do áudio) e intercalados em ordem cronológica correta — confirma CT-17 também, além da cobertura já existente em teste unitário. **Falta só a linha de base de WER (CT-36)**: o áudio usado nesta medição não era uma conversa real (era música tocada/cantada, útil pra medir tempo mas não pra WER com vocabulário de domínio), então a transcrição de referência feita à mão ainda precisa de uma reunião real de fato.

### Fase 4 · Resumo

Cadeia LangChain com Ollama local, provedor remoto opcional, prompts versionados, tratamento de transcrição longa.

**Pronto quando:** uma reunião real produz resumo com as quatro seções e responsável nas pendências, e a **rubrica comparativa contra o Notion AI está preenchida**.

**Esta é a fase que responde se o projeto valeu a pena.** Até aqui, o sistema faz o que outros já fazem. É o resumo em português com vocabulário de domínio que sustenta a decisão de construir em vez de instalar o pronto.

**Ideia registrada, não decidida ainda:** título gerado por IA a partir do conteúdo da reunião, substituindo o padrão `"Reunião {data} {hora}"` de hoje (docs/11-cli.md §3). Levantada em 2026-08-19 — a pergunta original também questionava se a *pasta* em disco deveria esperar esse nome antes de ser criada, mas isso não é viável: `cronista rec` cria a pasta no início da gravação, antes de existir qualquer conteúdo pra uma IA analisar, e gravação é irreversível (ADR-0006/ADR-0012), não dá pra adiar a escrita do áudio. O caminho mais provável, a decidir quando esta fase chegar: a pasta em disco continua nascendo por data/hora, estável; o título "bonito" vira só o campo `title` no banco, atualizado depois do resumo, sem renomear diretório físico.

### Fase 5 · Consulta e busca

Listagem, leitura de transcrição e resumos, busca com stemming de português.

**Pronto quando:** buscar "decisão" encontra "decidimos" em reunião de semanas atrás, em menos de 1 segundo.

**É a fase que transforma um monte de reuniões em acervo.** Sem busca, o valor decai com o tempo: ninguém relê a transcrição de três meses atrás procurando algo à mão.

### Fase 6 · Importação de arquivo

`cronista importar`, conversão com ffmpeg, reaproveitando o endpoint da Fase 2.

**Pronto quando:** um mp3 antigo vira reunião transcrita e resumida.

**Fase barata por construção.** Toda a espinha já existe; o que entra é conversão de formato. O que ela **não** resolve: arquivo importado tem trilha única, então os segmentos ficam com falante `desconhecido`. Elevar isso exigiria diarização, decisão adiada em [ADR-0007](adr/0007-fonte-de-audio-plugavel.md).

### Fase 7 · Retenção e exclusão

Política por idade, compressão ou remoção de áudio, exclusão em cascata com confirmação.

**Pronto quando:** áudio antigo é tratado conforme a política e reunião não transcrita **nunca** é tocada.

### Fase 8 · Interface desktop

PySide6 com ícone na bandeja, sobre a mesma API. Terá especificação própria.

### Fase 9 · Leitura remota

Interface de leitura acessível de outra máquina, pela rede privada.

**Decisão em aberto:** Tailscale, LAN ou outra. Não bloqueia nada até aqui.

## 3. Por que esta ordem

| Escolha | Razão |
|---|---|
| Infraestrutura antes de tudo | Consequência da API como centro. Tentar adiar geraria retrabalho |
| Captura na Fase 2, antes de transcrever | É a única etapa irreversível. Quanto antes estiver sólida, menos reunião se perde durante o desenvolvimento |
| Transcrição antes de resumo | O resumo não tem entrada sem ela |
| Busca depois do resumo | Sem acervo, não há o que buscar |
| Importação depois da busca, apesar de barata | Nada depende dela, e ela depende de tudo |
| Desktop por último entre as funcionais | A linha de comando já entrega o valor; a interface é conforto |

## 4. Decisões em aberto

Nenhuma bloqueia o início.

| Em aberto | Quando decidir |
|---|---|
| Modelo do Ollama | Fase 4, medindo em português real |
| Exposição na rede | Fase 9 |
| Diarização em arquivos importados | Fase 6, se o resumo sofrer sem falante |

## 5. Fora do roadmap

Registrado para não voltar como suposição: multiusuário, bot em reunião, transcrição em tempo real, aplicativo móvel, integrações e tradução. Todos em [01-documento-de-visao.md](01-documento-de-visao.md) §8.
