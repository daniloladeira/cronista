# Nome do Projeto

> **Status: em aberto, por decisão deliberada.**
> **Última atualização:** 2026-08-12

## 1. Situação

O projeto ainda não tem nome. Cinco rodadas de sugestão não produziram nenhum que agradasse, e a decisão foi **adiar** em vez de escolher por cansaço.

Isso não bloqueia nada. Até que apareça, valem os identificadores provisórios:

| Item | Provisório |
|---|---|
| Pacote Python | `meet_transcript` |
| Executável | `meet` |
| Repositório | `meet-transcript` |
| Banco de dados | `meet_transcript` |

## 2. Critérios

Do que a discussão revelou sobre o que se procura:

- **Vernacular** — português brasileiro, não inglês genérico
- **Não formal demais** — Ata, Escriba e Pauta soaram burocráticos
- **Não gíria demais** — Prosa, Papo e Resenha soaram informais demais
- **Curto no terminal** — é digitado várias vezes ao dia
- **Sem conflito óbvio** com produto existente

O espaço entre "formal demais" e "informal demais" é estreito, e é isso que torna a escolha difícil.

## 3. Candidatos considerados

Registrados para não refazer o trabalho. Nenhum foi aceito.

| Ângulo | Candidatos |
|---|---|
| Registro formal | Ata · **Minuta** · Súmula · Registro · Caderneta · Fichário · Memo |
| Pessoa ou papel | Escriba · Escrivão · **Relator** · Cronista · Taquígrafo · Caxias · Testemunha |
| Escuta | **Tímpano** · Orelhão · Antena · Radinho · Escuta · Ouvido · Eco · Sussurro |
| Conversa | Prosa · Papo · Resenha · Bate-papo · Falaê · Diga |
| Folclore e bichos | Saci · Curupira · Boitatá · Sabiá · Curió · Mainá |
| Inventado | Notari · Memora · Reunia · Atali · Resumia |
| Objeto ou marca | Cola · Rabisco · Bilhete · Recado |

**Os três que chegaram mais perto**, se a discussão for retomada:

- **Minuta** — termo brasileiro para rascunho de documento oficial, e trocadilho com *minutes*, que é ata em inglês. Funciona nos dois idiomas.
- **Relator** — quem relata e sintetiza. Peso institucional, sem soar corporativo genérico.
- **Tímpano** — a membrana que converte som em sinal, que é literalmente a função do sistema. O mais distinto de tudo que existe no mercado.

## 4. Procedimento de renomeação

Quando o nome aparecer, isto é o que muda. Feito antes da Fase 2, o custo é baixo; depois de existirem dados reais, o item 6 passa a exigir migração.

| # | Onde | O que muda |
|---|---|---|
| 1 | `pyproject.toml` | `name` do projeto e o executável em `[project.scripts]` |
| 2 | `meet_transcript/` | Nome do diretório do pacote |
| 3 | Todos os `import` | Referências ao pacote |
| 4 | `docs/` | Menções nos documentos — o texto foi escrito evitando o nome justamente para reduzir isto |
| 5 | `.env.example`, `docker-compose.yml` | Nome do serviço e do container |
| 6 | Banco e diretório de dados | Nome do banco e a pasta em `%LOCALAPPDATA%` |
| 7 | Repositório | Nome no controle de versão |

**Ordem recomendada:** fazer os itens 1 a 5 em um único commit dedicado, sem misturar com mudança funcional, para que o diff seja legível como renomeação. Os itens 6 e 7 depois, separadamente.

**Se o nome só aparecer depois de a Fase 2 estar em uso**, o item 6 exige migrar o banco e mover o diretório de gravações — e os caminhos guardados são relativos justamente para que isso seja possível sem tocar em nenhuma linha do banco ([ADR-0004](adr/0004-uuid-timestamptz-caminhos-relativos.md)).

## 5. Uma observação

Nomes bons costumam aparecer depois que a coisa existe e se sabe o que ela é. Adiar não é indecisão: é reconhecer que a informação necessária ainda não chegou.
