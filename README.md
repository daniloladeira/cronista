# Cronista

Grava reuniões direto do computador, transcreve **localmente** e gera resumos estruturados em português. Sem bot entrando na chamada, sem cota de uso, sem mensalidade, e sem o áudio sair da máquina.

*Cronista: quem registra o que aconteceu, na ordem em que aconteceu.*

> ## Estado atual: especificação
>
> **Ainda não há código.** Este repositório contém, por ora, a engenharia de requisitos e a especificação técnica completas. A implementação começa pela Fase 1 do [roadmap](docs/15-roadmap.md).

## Por que existe

Ferramentas de IA para reunião, em geral, cobram mensalidade ou limitam o recurso principal no plano gratuito, e enviam o áudio da reunião para a nuvem do fornecedor.

Existem projetos open-source que resolvem um problema semelhante, como [Meetily](https://github.com/Zackriya-Solutions/meetily) e [Hyprnote](https://github.com/fastrepl/hyprnote), ambos locais e de código aberto — nenhum dos dois é descartado aqui por deficiência técnica. O foco deste projeto é outro: **qualidade de transcrição e resumo em português brasileiro, com vocabulário de domínio**, área em que ferramentas com foco no inglês tendem a ter desempenho mais fraco.

Se esse foco se traduz em vantagem real é uma pergunta empírica. Há um [plano de testes](docs/14-plano-de-testes.md) que mede isso, com métrica objetiva de transcrição (WER) e rubrica comparativa de resumo contra o Notion AI. O resultado é publicado aqui, **inclusive se for desfavorável**.

## Como funciona

Duas trilhas de áudio gravadas separadamente, microfone e saída do sistema, dão a separação entre "você" e "os outros" **sem diarização**, de graça e sem erro de atribuição. Cada trilha é transcrita na GPU local e mesclada por instante.

```mermaid
flowchart LR
    A["Microfone<br/>+ loopback"] --> B["2 trilhas WAV<br/>em disco local"]
    B --> C["Transcrição<br/>GPU local"]
    C --> D["Mesclagem<br/>por instante"]
    D --> E["Resumo<br/>modelo local"]
    E --> F["Pauta · Decisões<br/>Pendências · Em aberto"]
```

**A gravação nunca depende da API.** O áudio vai para o disco antes de qualquer chamada de rede. Se o banco estiver fora do ar, a reunião é gravada do mesmo jeito e o registro se completa depois. Áudio de reunião não se regrava, e essa é a única falha irreversível do sistema. Ver [ADR-0012](docs/adr/0012-gravacao-em-disco-antes-da-api.md).

## Pilha

| Camada | Escolha |
|---|---|
| Captura | WASAPI com loopback, 16 kHz mono, duas trilhas |
| Transcrição | faster-whisper `large-v3` quantizado, em container com GPU via WSL2 |
| Resumo | LangChain com Ollama local; provedor remoto opcional |
| API | FastAPI, JWT de usuário único |
| Banco | PostgreSQL com busca `tsvector` e stemming de português |
| Interface | Linha de comando primeiro; desktop na Fase 8 |

## Documentação

### Engenharia de requisitos

| Documento | Conteúdo |
|---|---|
| [01 · Documento de Visão](docs/01-documento-de-visao.md) | Problema, posicionamento, recursos, restrições, não-objetivos |
| [02 · Glossário](docs/02-glossario.md) | Termos do domínio |
| [03 · Requisitos](docs/03-requisitos.md) | 31 funcionais e 22 não-funcionais, por FURPS+ |
| [04 · Modelo de Casos de Uso](docs/04-modelo-de-casos-de-uso.md) | Atores e diagrama |
| [05 · Detalhamento dos Casos de Uso](docs/05-detalhamento-casos-de-uso.md) | 11 casos de uso, 22 fluxos de exceção |
| [06 · Matriz de Rastreabilidade](docs/06-matriz-rastreabilidade.md) | Cobertura recurso, requisito, caso de uso, teste |

### Especificação técnica

| Documento | Conteúdo |
|---|---|
| [07 · Arquitetura](docs/07-arquitetura.md) | Componentes, implantação, fluxos, degradação |
| [08 · Modelo de Dados](docs/08-modelo-de-dados.md) | Esquema, estados, entidade-relacionamento, retenção |
| [09 · API](docs/09-api.md) | Contrato dos endpoints |
| [10 · Autenticação](docs/10-autenticacao.md) | JWT, postura de exposição |
| [11 · Linha de Comando](docs/11-cli.md) | Comandos e o que funciona offline |
| [12 · Transcrição](docs/12-transcricao.md) | Pipeline, modelo, vocabulário de domínio |
| [13 · Resumo](docs/13-resumo.md) | Cadeia, formato de saída, transcrições longas |

### Processo

| Documento | Conteúdo |
|---|---|
| [14 · Plano de Testes](docs/14-plano-de-testes.md) | 40 casos de teste, WER, rubrica de resumo |
| [15 · Roadmap](docs/15-roadmap.md) | Nove fases com critério de pronto |
| [16 · Nome](docs/16-nome.md) | Candidatos e procedimento de renomeação |
| [17 · Identidade Visual e Animação do CLI](docs/17-identidade-visual-cli.md) | Rich, barras de gradiente, papéis semânticos de cor |
| [ADRs](docs/adr/) | 17 decisões, cada uma com gatilho de reversão |
| [Referência Rich](docs/referencia-rich.md) | Guia técnico de implementação — não é spec, é atalho pra não redescobrir API |

## Decisões

Cada decisão técnica tem registro com contexto, consequências **negativas** e a condição concreta que a tornaria errada.

Duas merecem destaque por serem incomuns:

**[ADR-0005 · LangChain](docs/adr/0005-langchain-na-camada-de-resumo.md)** foi adotado *contra* a recomendação técnica registrada no próprio documento. O ADR preserva o desacordo em vez de reescrever a história.

**[ADR-0012 · Gravação antes da API](docs/adr/0012-gravacao-em-disco-antes-da-api.md)** é a única exceção deliberada à arquitetura, e o único ADR sem gatilho de reversão.

## Ambiente

Windows 11, Python 3.13, GPU NVIDIA, Docker Desktop (backend WSL2, com suporte a GPU NVIDIA), Ollama, ffmpeg (`winget install Gyan.FFmpeg`). O ffmpeg só é necessário para `cronista importar` (Fase 6).

A captura de loopback foi verificada nesta máquina antes do planejamento. O script está em [`scripts/check_audio.py`](scripts/check_audio.py) e é o primeiro passo de qualquer instalação.

```powershell
.\.venv\Scripts\python.exe scripts\check_audio.py
```

Todos os comandos abaixo são do PowerShell, na pasta do projeto. O ambiente virtual tem que se chamar `.venv` e ficar na raiz do repositório: o `cronista-tui` chama `.venv\Scripts\cronista.exe` e `.venv\Scripts\python.exe` por esse caminho.

### Instalação (primeira vez)

**1. Dependências Python e Node**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd cronista-tui; npm install; cd ..
```

**2. Configuração.** Copie o modelo e edite o `.env` (ele está no `.gitignore`, nunca vai para o repositório):

```powershell
Copy-Item .env.example .env
```

Três valores precisam ser gerados, não inventados:

```powershell
# JWT_SECRET: segredo aleatório e longo
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"

# AUTH_PASSWORD_HASH: pede a senha duas vezes e imprime o hash Argon2
.\.venv\Scripts\python.exe scripts\hash_password.py
```

`DATA_ROOT` é onde fica o áudio. Recomendado: `C:\Users\SEU_USUARIO\AppData\Local\cronista`. Cliente, API e worker leem a mesma raiz.

**3. Banco, worker e esquema**

```powershell
docker compose up -d --build
.\.venv\Scripts\python.exe -m alembic upgrade head
```

**4. Resumo (Ollama).** Baixe o modelo que estiver em `OLLAMA_MODEL` no `.env`:

```powershell
ollama pull llama3.1:8b
```

**5. Token do worker (só se quiser resumo automático).** Grava no `.env` sem mostrar o token, depois recria o worker para ele ler o valor. Ligue também `WORKER_AUTO_SUMMARIZE=true`.

```powershell
$t = .\.venv\Scripts\python.exe scripts\mint_worker_token.py; (Get-Content .env) -replace '^WORKER_SERVICE_TOKEN=.*', "WORKER_SERVICE_TOKEN=$t" | Set-Content .env -Encoding utf8
docker compose up -d worker
```

### Subir o ambiente (todo dia)

O banco e o worker têm `restart: unless-stopped`: voltam sozinhos quando o Docker Desktop abre. Se não voltaram:

```powershell
docker compose up -d
```

**A API não está no compose.** Sobe à parte, e fica rodando em um terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn cronista.api.main:app --host 127.0.0.1 --port 8000
```

### Usar

Em outro terminal. O menu (`cronista` sem argumentos) abre o `cronista-tui` e cobre Reuniões, Dispositivos, Login, Gravar e Sincronizar. Os comandos diretos servem para script:

```powershell
cronista                                  # menu
cronista login                            # autentica (também existe no menu)
cronista devices                          # microfones e saídas disponíveis
cronista rec --titulo "Alinhamento"       # grava até Ctrl+C; --mic e --saida escolhem dispositivo
cronista sync                             # reenvia reuniões gravadas com a API fora do ar
cronista importar C:\caminho\audio.mp3    # importa áudio ou vídeo (precisa do ffmpeg)
cronista list                             # lista reuniões
cronista ler <id>                         # transcrição e resumo
cronista buscar "decisão"                 # busca com stemming de português
cronista resumir <id>                     # gera um novo resumo
cronista reprocessar <id>                 # retranscreve
cronista excluir <id>                     # apaga áudio e registro, pede confirmação
```

Se `cronista` não for reconhecido no PowerShell, use `.\.venv\Scripts\cronista.exe`.

### Diagnóstico

Log do worker. Junte os dois fluxos, senão os logs do Python não aparecem:

```powershell
docker logs -f cronista-worker 2>&1
```

Testes (usam o banco `cronista_test`, criado pelo compose na primeira vez):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

Reuniões que falharam e o motivo:

```powershell
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select audio_dir, status, left(error, 200) from meetings where status like ''%failed'';"' 2>$null
```

**Esquecer de subir não custa uma reunião.** Gravar não depende de API nem de banco. O áudio vai para o disco e o registro se completa depois, com `cronista sync`. É exatamente o cenário que motivou o [ADR-0012](docs/adr/0012-gravacao-em-disco-antes-da-api.md): ninguém confere container antes de entrar numa reunião.

---

*Documentação em português por decisão deliberada: o projeto é para uso em português e a clareza para quem o mantém vale mais que alcance internacional. Identificadores de código e esquema seguem em inglês.*
