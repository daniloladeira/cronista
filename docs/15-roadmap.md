# Roadmap

> **Versão:** 1.2 · **Última atualização:** 2026-08-22

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

**CT-16 medido em 2026-08-21, com reunião real: passou com folga larga.** Reunião de 59min39s (duas trilhas, `voce` e `outros`), gravada e reprocessada pelo pipeline completo (`cronista rec` → API → fila → `cronista-worker` em container com GPU). Do momento em que o worker reivindicou a reunião (checagem do modelo no Hugging Face) até o modelo voltar a ficar ocioso: **~2min26s**, medido pelos timestamps do log do worker (claim às 12:02:34, última atividade do modelo entre 12:04:58 e 12:05:04, inferido do log de descarregamento por ociosidade 300s depois). Ou seja, ~24x mais rápido que tempo real — a fronteira 9P WSL↔Windows não se mostrou um gargalo relevante nessa medição; a cópia pro WSL cogitada como saída de contingência não foi necessária. 1069 segmentos persistidos (924 `outros`, 145 `voce`), cobrindo a reunião inteira (`max(end_ms)` bate com a duração do áudio) e intercalados em ordem cronológica correta — confirma CT-17 também, além da cobertura já existente em teste unitário. **Falta só a linha de base de WER (CT-36)**: o áudio usado nesta medição tinha fala real, mas misturada com um vídeo do YouTube tocando junto — útil pra medir tempo, mas não serve de referência de WER (não é a conversa de domínio limpa que CT-36 pede). A transcrição de referência feita à mão ainda precisa de uma reunião real, sem essa mistura.

**CT-36 medido em 2026-08-22, sobre os primeiros 20min dessa mesma reunião: WER 0,0%** (1755 palavras, 0 substituições/remoções/inserções), com `scripts/measure_wer.py`. Aceito como linha de base — decisão do usuário. **Nota de método, por transparência sobre como o número foi obtido:** a referência (`ct36/referencia_20min.txt`) partiu de uma cópia da própria saída do Whisper, revisada de ouvido; na conferência, o usuário identificou de verdade três problemas pontuais (um loop de alucinação repetindo "Me agrada" várias vezes, "cheerleader" transcrito como "char leader", e uma repetição de "e" de origem incerta), e mesmo assim aprovou seguir com o arquivo como estava. Fase 3 considerada concluída com essa medição.

### Fase 4 · Resumo

Cadeia LangChain com Ollama local, provedor remoto opcional, prompts versionados, tratamento de transcrição longa.

**Pronto quando:** uma reunião real produz resumo com as quatro seções e responsável nas pendências, e a **rubrica comparativa contra o Notion AI está preenchida**.

**Esta é a fase que responde se o projeto valeu a pena.** Até aqui, o sistema faz o que outros já fazem. É o resumo em português com vocabulário de domínio que sustenta a decisão de construir em vez de instalar o pronto.

**Etapas 1-5 implementadas e auditadas contra CT-21 a CT-24 em 2026-08-22** ([docs/14-plano-de-testes.md](14-plano-de-testes.md) §3.4):

| ID | Status |
|---|---|
| CT-21 (4 seções + responsável) | ✅ Validado com transcrição sintética contra Ollama real (`llama3.1:8b`), depois de 3 rodadas de prompt (v1→v3, docs/13 §4) |
| CT-22 (transcrição maior que a janela) | ✅ Mecanismo de blocos + consolidação (RF-17) testado e validado contra Ollama real; qualidade da consolidação em fragmentação extrema tem ressalva registrada (docs/13 §5) |
| CT-23 (provedor fora do ar, mensagem acionável) | ✅ Corrigido na auditoria — a mensagem só nomeava o provedor, não dizia como iniciá-lo; agora inclui (`ollama serve`, checar `ANTHROPIC_API_KEY`) |
| CT-24 (nunca sobrescreve) | ✅ Testado (RN-03) |

**O que falta pro "pronto quando" desta fase: uma reunião REAL, não sintética, resumida bem, e a rubrica comparativa (CT-37).** Toda a validação com Ollama até aqui usou transcrição sintética (fictícia, tom de reunião normal) — a única reunião real disponível (a do CT-16/36) foi recusada pelo próprio modelo por causa do áudio misturado com YouTube (mesmo bloqueio de material que já afetava o CT-36). Isso não invalida a implementação nem os testes, mas significa que **o critério de "pronto" da Fase 4 continua em aberto** até existir uma reunião real de domínio pra medir contra — exatamente o mesmo tipo de bloqueio que o CT-36 teve na Fase 3.

**Primeira medição com reunião real em 2026-08-22** (reunião de alinhamento sobre migração de dados clínicos do iClinic — domínio real, ~21 mil caracteres, forçou o caminho de blocos do RF-17 em escala real, não artificial). Dois achados:

1. **Formatação: achado e corrigido de novo.** A consolidação voltou a usar `### ` (nível 3) em vez de `## `, o mesmo bug do CT-22 — mas dessa vez na chamada de consolidação, não nos blocos. `_PROMPT_CONSOLIDACAO` reforçado com instrução negativa explícita ("não nível 3, mesmo que os pedaços recebidos estejam em outro nível"); corrigiu na segunda tentativa.
2. **Conteúdo: qualidade real ainda tem lacuna.** Com a formatação certa, "Decisões" saiu **vazio**, apesar da reunião ter decisões claras (não importar dados de agenda, não importar dados financeiros, priorizar simplicidade). E duas "Pendências"/"Pontos em aberto" saíram **invertidas** — o resumo sugeriu "importar dados financeiros" e "importar agendamentos futuros" quando a reunião decidiu o oposto dos dois.

**Prompt v4** (docs/13 §4): reforçou "Decisões" pra reconhecer o padrão pergunta→explicação→concordância (não só "decidimos X" explícito), e adicionou instrução redobrada sobre preservar negação. Resultado, testado de novo contra a mesma reunião real:

- ✅ **A inversão do financeiro foi corrigida** — agora diz corretamente "Não importar as informações financeiras do iClinic". "Decisões" saiu com 4 itens reais, não mais vazio.
- ❌ **Novo problema: a decisão sobre agenda sumiu inteira** — nem aparece certa, nem errada, nem em Decisões nem em Pontos em aberto. Antes pelo menos aparecia (invertida); agora foi perdida na consolidação.
- ❌ **Leve fabricação de justificativa**: duas decisões vieram com motivo que não foi dito na reunião ("de acordo com a legislação brasileira", "pode causar problemas de sincronização com a agenda") — não é inversão de fato, mas é conteúdo que a transcrição não sustenta, o tipo de coisa que o prompt já proíbe explicitamente e mesmo assim aconteceu.

**Comparação com `gemma2:9b`** (mesmo prompt v4, mesma reunião real, ~5,4GB — cabe no orçamento de VRAM documentado em [07-arquitetura.md](07-arquitetura.md) §3 pro modelo de resumo, diferente do `llama3.1:8b` que é Meta, o `gemma2` é Google): **não foi uma vitória clara.** Trocou um conjunto de falhas por outro, não removeu falha nenhuma:

- "Pauta" saiu duplicada — dois blocos de marcador diferente (`*` e `-`) com conteúdo sobreposto, mal fundidos na consolidação.
- Uma pendência real ("resolver o problema do endereço não vinculado") foi classificada como Decisão.
- A decisão sobre dados financeiros virou uma pergunta em "Pontos em aberto" com a resposta escrita entre parênteses ("Definir como lidar... (não importar)") — trata algo já decidido como se ainda estivesse em aberto.
- A decisão sobre agenda sumiu inteira, mesmo problema do `llama3.1:8b`.

**Não fecha o "pronto quando" ainda.** Quatro rodadas de prompt (v1→v4) e dois modelos testados hoje contra a mesma reunião real — cada ajuste resolve um problema e revela outro, e trocar de modelo (dentro da faixa que cabe no orçamento de VRAM desta máquina) trocou de defeito, não removeu defeito. Isso é evidência real de que o gargalo não é (só) escolha de modelo ou texto de prompt — pode ser a abordagem de bloco+consolidação em si, nessa faixa de tamanho de modelo (8-9B).

**Causa raiz encontrada: a divisão em blocos não era necessária pra essa reunião.** `summary_context_chars=12.000` tinha sido calibrado em cima do `default_num_ctx=4096` que o Ollama escolhe sozinho — não o teto real do modelo, só o que ele achou "seguro" sem eu pedir mais explicitamente. Pesquisei o padrão (map-reduce perde contexto entre blocos é problema conhecido; ver [ADR](https://www.toolify.ai/ai-news/langchain-summarization-mapreduce-vs-refine-methods-3395910)) e testei a hipótese mais barata primeiro: aumentar a janela de contexto pra caber a reunião inteira numa chamada só, sem dividir.

**Confirmado.** Com `ollama_num_ctx=8192` (`ChatOllama` aceita isso direto, `cronista/api/summarize.py` `_modelo()`) e `summary_context_chars=24.000` (a reunião de ~21 mil caracteres já não precisa dividir), rodando a mesma reunião real numa única chamada: **a decisão sobre agenda voltou a aparecer, corretamente negada** ("A importação dos dados de agenda não compensa..."). Medido, não presumido: 6,7GB de VRAM usados (RTX 4060, 8GB total) sem derramar pro CPU, resposta em ~11s — funcionou, com pouca folga sobrando. Três variantes de formatação apareceram no processo (nível 3 puro, `### ##` colado, negrito em volta do título) — em vez de perseguir cada uma, `_normalizar_titulos()` agora aceita qualquer nível de cabeçalho reconhecível (1-6, com ou sem negrito) e normaliza pro nível 2 canônico antes de validar; a garantia real (seção tem que aparecer de verdade) continua intacta.

**Estado atual, honesto:** o problema mais grave (decisão inteira desaparecendo/invertendo) melhorou substancialmente ao evitar a divisão em blocos pra reuniões que cabem na janela maior — mas não é garantia de 100%. Numa nova rodada, a decisão sobre dados financeiros (que apareceu certa em testes anteriores) não apareceu nessa execução — variação normal de amostragem do modelo, não um bug determinístico. E negação em LLM é fraqueza documentada na literatura (ver plano de pesquisa em `swift-zooming-thacker.md`), não algo que qualquer ajuste "resolve" de vez — fica como risco residual conhecido, mitigado, não eliminado. `summary_block_overlap_segments` e a lógica de blocos continuam existindo pra reuniões genuinamente maiores que 24 mil caracteres (~1h30 de fala densa); não foi testado nesse tamanho ainda.

**Mais perto do "pronto quando", mas ainda não fechado** — falta medir mais reuniões reais (uma só não é amostra suficiente) e a rubrica comparativa (CT-37).

**Ideia registrada, não decidida ainda:** título gerado por IA a partir do conteúdo da reunião, substituindo o padrão `"Reunião {data} {hora}"` de hoje (docs/11-cli.md §3). Levantada em 2026-08-19 — a pergunta original também questionava se a *pasta* em disco deveria esperar esse nome antes de ser criada, mas isso não é viável: `cronista rec` cria a pasta no início da gravação, antes de existir qualquer conteúdo pra uma IA analisar, e gravação é irreversível (ADR-0006/ADR-0012), não dá pra adiar a escrita do áudio. O caminho mais provável, a decidir quando esta fase chegar: a pasta em disco continua nascendo por data/hora, estável; o título "bonito" vira só o campo `title` no banco, atualizado depois do resumo, sem renomear diretório físico.

### Fase 5 · Consulta e busca

Listagem, leitura de transcrição e resumos, busca com stemming de português.

**Pronto quando:** buscar "decisão" encontra "decidimos" em reunião de semanas atrás, em menos de 1 segundo.

**É a fase que transforma um monte de reuniões em acervo.** Sem busca, o valor decai com o tempo: ninguém relê a transcrição de três meses atrás procurando algo à mão.

**Etapa 1 (API somente leitura) implementada em 2026-08-22**: `GET /meetings/{id}` (RF-20/22, com trilhas e resumos), `GET /meetings/{id}/transcript` (RF-21), `PATCH /meetings/{id}` (renomear), `GET /search` (RF-23/24). Painel Textual (ADR-0016) e auditoria contra CT-25-29 ficam pra próxima etapa.

**Achado real, construindo o `GET /search`: o "pronto quando" desta fase, como escrito, era falso com o Postgres padrão.** Testei o exemplo do próprio CT-27 direto no banco, fora do meu código: `to_tsvector('portuguese', 'decidimos') @@ plainto_tsquery('portuguese', 'decisão')` dava **falso**. Pior: nem "decisão"/"decisões" (plural da mesma palavra) o dicionário `portuguese` padrão junta — o padrão -ão/-ões é irregular em português e o stemmer por sufixo (snowball) não trata bem esse caso. Isso não era só uma lacuna de teste: [docs/08-modelo-de-dados.md](08-modelo-de-dados.md) já afirmava, como parte da razão de ter escolhido Postgres em vez de SQLite, que isso funcionava — estava documentado errado.

**Conserto, em duas camadas, medido até funcionar de verdade:**

1. **Dicionário hunspell de português** (`hunspell-pt-br`, pacote `apk` do Alpine — mesma base do `postgres:17-alpine` já usado), encadeado antes do stemmer padrão. Resolve flexão irregular (plural -ão/-ões). Exigiu conversão de codificação dos arquivos do dicionário (ISO-8859-1 → UTF-8) que o Postgres **não** faz sozinho a partir da declaração `SET` do arquivo — testado, deu erro de bytes inválidos antes de eu perceber isso.
2. **Dicionário de sinônimos, escrito à mão** (`docker/db/tsearch_data/pt_br_sinonimos.syn`), encadeado antes do hunspell. Resolve o que nem hunspell resolve: "decisão" (substantivo) e "decidir" (verbo) são palavras derivacionalmente relacionadas, não uma variação flexional da mesma palavra — nenhum dicionário de flexão (snowball ou hunspell) junta as duas sozinho. O arquivo mapeia `decisão`/`decisões` pro verbo, que já reduzia certo. Começou pequeno, só o par que o CT-27 cita — crescer isso pra vocabulário de domínio mais amplo é ideia registrada, não decidida, no mesmo espírito de RF-13/`WHISPER_VOCABULARY`.

Confirmado nos dois bancos (dev e teste) e via `GET /search` de ponta a ponta: os três casos batem agora — `decisão`/`decidimos`, `decisão`/`decisões`, e a conjugação verbal que já funcionava antes (`decidir`/`decidiu`/`decidimos`) continua funcionando. `docs/08-modelo-de-dados.md` corrigido pra não afirmar mais algo que não era verdade.

**Etapa 2 (painel navegável) implementada em 2026-08-22**: `cronista list`/`ler`/`buscar` convergem num único painel Textual (`cronista/client/panel.py`, ADR-0016) — lista de reuniões à esquerda, abas Transcrição/Resumo à direita (`TabbedContent`, `Markdown` widget pro resumo), busca embutida na tecla `/` que repopula a lista sem sair da tela. Fora de terminal interativo, os três comandos caem num fallback de texto puro (tabela/transcrição impressa), sem tentar abrir Textual sem TTY.

Seguindo a regra que o próprio ADR-0016 registrou depois da primeira tentativa rejeitada ("horrível, horrível, horrível"): exportado SVG do painel em dois estados antes de tocar no `cli.py`, e a inspeção real (não só visual, lendo as linhas de texto extraídas) achou um problema de verdade — título de reunião longo quebra em duas linhas na lista, e sem espaçamento colava direto no item seguinte. Corrigido (`margin-bottom` no `ListItem`) e reconferido antes de prosseguir.

**Achado real testando os três comandos contra dados de verdade**: o processo da API rodando havia sido iniciado horas antes de toda essa fase — `GET /meetings`, que já existia desde a Fase 2, funcionava; `/meetings/{id}`, `/transcript` e `/search`, todos novos, devolviam 404 mesmo existindo no código e passando nos testes (que sempre usam uma instância nova da app, não o processo real rodando). Reiniciar o processo resolveu — lição prática: testes passando não substituem validar contra o processo real de pé, principalmente numa sessão longa onde o código mudou depois do processo já estar rodando.

**Auditoria formal contra CT-25 a CT-29 (2026-08-22): quatro dos cinco já tinham teste automatizado; um não tinha.**

| CT | Cobertura | Onde |
|---|---|---|
| CT-25 | ✅ | `test_meeting_detail.py` (estado + trilhas + resumos), `test_transcript.py` (transcrição) |
| CT-26 | ✅ | `test_get_transcript_sem_segmento_devolve_lista_vazia_nao_erro` — reunião `status="recorded"` (ainda sem transcrever) devolve `200 []`, não erro |
| CT-27 | ✅ | `test_search_por_decisao_encontra_decidimos_stemming_portugues` |
| CT-28 | ⚠️ → ✅ | não tinha teste algum — corrigido nesta auditoria, ver abaixo |
| CT-29 | ✅ | `test_search_sem_resultado_devolve_lista_vazia_com_200` |

**CT-28 ("busca responde em menos de 1 segundo") era a lacuna real.** Escrever um teste com os 2-3 segmentos sintéticos que os outros testes usam não provaria nada — GIN index ou não, qualquer busca em 3 linhas é instantânea. Adicionei `test_search_responde_em_menos_de_1_segundo_com_volume_realista` (`tests/test_search.py`) que semeia 5.000 segmentos reais (Postgres de teste, não mock) antes de medir. 5.000 porque o banco de dev real tem 1.136 hoje — dá margem sem depender do tamanho atual do acervo, que só cresce.

Medido dos dois jeitos, não só presumido pelo índice GIN existir:
- **Contra o banco de dev real** (1.136 segmentos, `GET /search?q=decisão` via curl, token real): três chamadas, ~215-227ms cada.
- **Contra o teste automatizado** (5.000 segmentos sintéticos, TestClient): passa com folga, muito abaixo de 1s.

Fase 5 fechada.

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
