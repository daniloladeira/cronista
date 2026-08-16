# ADR-0009 · SQLAlchemy e Alembic

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** RNF-S02

## Contexto

Decidido o PostgreSQL ([ADR-0003](0003-postgres-como-banco.md)), restava como acessá-lo. Três caminhos: driver puro com SQL escrito à mão e migrações numeradas; SQLAlchemy Core, com construtor de consultas mas sem mapeamento de objetos; ou SQLAlchemy completo com Alembic.

O esquema é pequeno — quatro tabelas. Um driver puro daria conta e manteria o SQL visível.

## Decisão

Usar **SQLAlchemy com Alembic**. Escolha do usuário, coerente com a preferência já manifestada por ferramental estabelecido ([ADR-0005](0005-langchain-na-camada-de-resumo.md)).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| `psycopg` + arquivos SQL numerados | Mais leve e mantém o SQL à vista, mas exige escrever a mecânica de migração à mão |
| SQLAlchemy Core, sem mapeamento | Meio-termo razoável; preterido por preferência |

## Consequências

**Positivas.** Alembic resolve migração versionada, que RNF-S02 exige, sem código próprio. Modelos servem de documentação executável do esquema. Ferramental amplamente conhecido, o que ajuda num repositório de portfólio.

**Negativas.** Camada de abstração sobre um esquema que não precisa dela. Recursos específicos do PostgreSQL usados aqui — coluna `tsvector` gerada, índice GIN, `FOR UPDATE SKIP LOCKED` — exigem SQL literal dentro dos modelos e das migrações, o que reduz parte do ganho. Alembic não detecta automaticamente tudo que este esquema usa; a revisão inicial precisa ser conferida à mão.

## Gatilho de reversão

Se a maior parte das consultas acabar escrita como SQL literal para acessar recursos do PostgreSQL, a camada estará custando sem entregar, e o driver puro passa a ser a escolha honesta. **Alembic ficaria de qualquer forma** — a mecânica de migração vale por si, independentemente de como o resto acessa o banco.
