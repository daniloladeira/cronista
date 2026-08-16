# Glossário

> **Versão:** 1.0 · **Última atualização:** 2026-08-12

Termos usados no restante da documentação. Organizado alfabeticamente.

---

**ADR** — *Architecture Decision Record*. Registro curto de uma decisão técnica: contexto, decisão, consequências e gatilho de reversão. Existe para que o **porquê** de uma escolha sobreviva ao tempo, não só a escolha. Ver [adr/](adr/).

**Argon2** — Algoritmo de hash de senha, vencedor da Password Hashing Competition. Usado para armazenar a credencial de acesso. Diferente de um hash comum, é deliberadamente lento e consome memória, o que encarece ataque por força bruta.

**Ata** — Registro do que foi tratado e decidido em uma reunião. É o produto final do sistema, embora aqui a palavra "resumo" seja usada com mais frequência.

**CTranslate2** — Motor de inferência que executa o modelo de transcrição. É o que permite rodar o Whisper com menos memória e mais velocidade que a implementação de referência. Base do `faster-whisper`.

**Diarização** — Processo de identificar *quem* falou cada trecho de um áudio de trilha única. Neste sistema ela é **evitada** na gravação ao vivo: gravar microfone e saída do sistema separadamente já distingue o usuário dos demais participantes, sem custo de processamento nem erro de atribuição. Volta a ser relevante apenas em arquivos importados. Ver [adr/0001-captura-local-duas-trilhas.md](adr/0001-captura-local-duas-trilhas.md).

**FURPS+** — Esquema de classificação de requisitos não-funcionais: *Functionality, Usability, Reliability, Performance, Supportability*, mais restrições (de design, implementação, interface e físicas). Usado em [03-requisitos.md](03-requisitos.md).

**GIN** — *Generalized Inverted Index*. Tipo de índice do PostgreSQL adequado a valores que contêm múltiplos elementos indexáveis — como um `tsvector`, que contém muitas palavras. É o que torna a busca textual rápida.

**JWT** — *JSON Web Token*. Token assinado que carrega a identidade do portador. O cliente o envia a cada requisição em vez de reenviar a senha. Ver [10-autenticacao.md](10-autenticacao.md).

**LangChain** — Framework de orquestração de chamadas a modelos de linguagem. Usado aqui na camada de resumo. A escolha e seu trade-off estão em [adr/0005-langchain-na-camada-de-resumo.md](adr/0005-langchain-na-camada-de-resumo.md).

**Loopback** — Captura do áudio que está **saindo** pela placa de som, isto é, o que o usuário está ouvindo. É o que permite gravar a fala dos outros participantes sem microfone apontado para a caixa de som. No Windows é fornecido pela WASAPI.

**Map-reduce (em sumarização)** — Estratégia para resumir texto maior que a janela de contexto do modelo: resume-se cada pedaço isoladamente (*map*) e depois resumem-se os resumos (*reduce*). Alternativa à janela deslizante. Ver [13-resumo.md](13-resumo.md).

**Ollama** — Servidor local que executa modelos de linguagem na máquina do usuário. É o provedor padrão de resumo do sistema, e o que sustenta a promessa de custo zero e dado local.

**Opus** — Codec de áudio com compressão eficiente em voz. Candidato para arquivar áudio antigo, reduzindo o consumo de disco em cerca de duas ordens de grandeza frente ao WAV. Ver política de retenção em [08-modelo-de-dados.md](08-modelo-de-dados.md).

**Quantização (`int8_float16`)** — Representação dos pesos do modelo com menos bits que o original. Reduz consumo de memória de vídeo e aumenta velocidade, com perda pequena de precisão. É o que faz o modelo grande caber com folga em 8 GB de VRAM.

**Reunião** — Entidade central do sistema. Agrega uma ou mais trilhas de áudio, os segmentos transcritos e os resumos gerados. Nasce de gravação ao vivo ou de importação de arquivo.

**Segmento** — Trecho contínuo de fala com início, fim e texto, atribuído a um falante. É a unidade que o modelo de transcrição devolve e a unidade armazenada — não se guarda a transcrição como bloco único de texto. Isso é o que permite saltar o áudio para um ponto, filtrar por falante e buscar com precisão.

**Stemming** — Redução de palavras ao radical, de modo que "decidimos", "decidido" e "decisão" sejam tratadas como a mesma raiz na busca. O PostgreSQL oferece stemming de português nativamente, e essa é uma das razões da escolha do banco. Ver [adr/0003-postgres-como-banco.md](adr/0003-postgres-como-banco.md).

**Trilha** — Um canal de áudio gravado independentemente. A gravação ao vivo produz duas (`voce`, do microfone; `outros`, do loopback); um arquivo importado produz uma. O pipeline de transcrição trabalha sobre uma **lista** de trilhas, nunca sobre um número fixo.

**tsvector** — Tipo do PostgreSQL que representa um documento já processado para busca textual: palavras normalizadas, com radical extraído e posições. Combinado a um índice GIN, é o mecanismo de busca do sistema.

**UUIDv7** — Identificador único de 128 bits cuja parte inicial é o instante de criação. Tem a unicidade global do UUID e, ao contrário das versões anteriores, é **ordenável por tempo** — o que preserva localidade em índice. Ver [adr/0004-uuid-timestamptz-caminhos-relativos.md](adr/0004-uuid-timestamptz-caminhos-relativos.md).

**VAD** — *Voice Activity Detection*. Detecção de presença de fala. Usada para descartar silêncio antes da transcrição, o que reduz tempo de processamento e evita que o modelo alucine texto em trechos mudos — problema real na trilha de loopback, que fica em silêncio sempre que ninguém mais fala.

**WASAPI** — *Windows Audio Session API*. Interface de áudio do Windows que fornece a captura de loopback usada pelo sistema.

**WER** — *Word Error Rate*. Métrica de qualidade de transcrição: proporção de inserções, remoções e substituições em relação a uma transcrição de referência. Quanto menor, melhor. É a métrica objetiva do sistema. Ver [14-plano-de-testes.md](14-plano-de-testes.md).

**Whisper / faster-whisper** — Whisper é o modelo de reconhecimento de fala usado. `faster-whisper` é a implementação sobre CTranslate2 adotada aqui, escolhida por caber na GPU disponível e transcrever mais rápido que o tempo real.

**Worker** — Processo separado da API que executa a transcrição. Consome trabalho lendo o estado das reuniões no banco — o banco é a fila. Roda apartado porque mantém o modelo carregado em memória de vídeo. Ver [07-arquitetura.md](07-arquitetura.md).
