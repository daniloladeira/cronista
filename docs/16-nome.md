# Nome do Projeto

> **Status: decidido — Cronista.**
> **Decidido em:** 2026-08-17 · **Última atualização:** 2026-08-17

## 1. O nome

**Cronista** — quem registra o que aconteceu, na ordem em que aconteceu.

| Item | Valor |
|---|---|
| Pacote Python | `cronista` |
| Executável | `cronista` |
| Repositório | `cronista` |
| Banco de dados | `cronista` |
| Diretório de dados | `%LOCALAPPDATA%\cronista` |

## 2. Por que este

**Descreve o papel, não o artefato.** "Ata", "Minuta" e "Súmula" nomeiam o documento produzido. O sistema, porém, faz o trabalho de uma *pessoa* que anotaria a reunião por você — e nomear o papel encaixa melhor no que o produto é.

**Cai na faixa que se procurava.** Cinco rodadas de sugestão fracassaram por oscilar entre extremos: Ata, Escriba e Pauta soaram formais demais; Prosa, Papo e Resenha, informais demais. Cronista fica entre os dois.

**Carrega um tom que nenhum outro candidato tinha.** No Brasil, "crônica" é gênero literário do cotidiano — Rubem Braga, Verissimo. O nome sugere registro bem-escrito e leve, em vez de burocrático. Para um sistema cujo entregável é texto lido por humano, isso conta.

**Não colide.** Não há software conhecido com esse nome.

**Nota sobre a extensão.** São oito caracteres, digitados várias vezes ao dia. Abreviar para `cron` foi **descartado**: colidiria de frente com o agendador do Unix. O autocompletar do terminal resolve na prática.

## 3. Candidatos considerados

Preservado como registro do processo, não como lista de pendências.

| Ângulo | Candidatos |
|---|---|
| Registro formal | Ata · Minuta · Súmula · Registro · Caderneta · Fichário · Memo |
| Pessoa ou papel | **Cronista** · Escriba · Escrivão · Relator · Taquígrafo · Caxias · Testemunha |
| Escuta | Tímpano · Orelhão · Antena · Radinho · Escuta · Ouvido · Eco · Sussurro |
| Conversa | Prosa · Papo · Resenha · Bate-papo · Falaê · Diga |
| Folclore e bichos | Saci · Curupira · Boitatá · Iara · Uirapuru · Sabiá · Curió · Mainá |
| Inventado | Notari · Memora · Reunia · Atali · Resumia |
| Objeto ou marca | Cola · Rabisco · Bilhete · Recado |

### 3.1 Uma armadilha que quase passou

Dois nomes da linha de folclore — **Curupira** e **Iara** — são personagens definidos por **enganar**. A Curupira tem os pés virados para trás justamente para desorientar quem a segue; a Iara canta para atrair e afogar.

Batizar assim um sistema cujo valor inteiro é fidelidade ao que foi dito, e cujo pior defeito possível é inventar uma decisão que não houve ([14-plano-de-testes.md](14-plano-de-testes.md) §5, alucinação é critério eliminatório), seria escolher um nome que significa o oposto do produto.

Nome arbitrário e memorável é estratégia legítima — Kafka, Hadoop, Puma não descrevem nada. Mas quando o nome **significa** alguma coisa, precisa não significar o contrário.

## 4. Renomeação: executada

Aplicada em 2026-08-17, antes de existir qualquer código — o momento mais barato possível.

| # | Onde | Estado |
|---|---|---|
| 1 | `pyproject.toml` — nome e executável | sim |
| 2 | Nome do pacote | sim |
| 3 | Menções na documentação | sim |
| 4 | `.env.example`, `docker-compose.yml` — banco, containers, volumes | sim |
| 5 | Diretório de dados em `%LOCALAPPDATA%` | feito na especificação |
| 6 | Diretório do repositório no disco | pendente |

O item 6 é movimentação de pasta no sistema de arquivos, feita fora do controle de versão. Nada depende dele: os caminhos de áudio são relativos por decisão do [ADR-0004](adr/0004-uuid-timestamptz-caminhos-relativos.md), e o repositório não tem remoto.

## 5. Observação

O nome apareceu depois que a especificação estava pronta — e apareceu com facilidade, quando cinco tentativas anteriores de forçá-lo haviam falhado. Adiar não foi indecisão: era falta de informação sobre o que a coisa era.
