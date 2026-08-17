# ADR-0003 · PostgreSQL como banco de dados

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** RF-23, RNF-P02
- **Substitui:** proposta inicial de usar SQLite

## Contexto

O sistema é de usuário único, roda em uma máquina, e o volume previsto é de alguns milhares de registros. SQLite atenderia com folga, e foi o que se recomendou inicialmente: um arquivo, sem servidor, backup por cópia.

Duas coisas mudaram a análise. O usuário manifestou preferência por PostgreSQL, e ao avaliar a consequência apareceu um argumento técnico que a recomendação inicial não tinha considerado: **busca textual com stemming de português**. O PostgreSQL traz o dicionário `portuguese` nativo: "decidimos", "decidido" e "decisão" colapsam na mesma raiz. O mecanismo equivalente do SQLite não faz stemming de português.

Num sistema cuja tese é qualidade em português, isso deixa de ser detalhe.

## Decisão

Usar **PostgreSQL** em container Docker sobre WSL2. Busca textual com coluna `tsvector` gerada, dicionário `portuguese`, e índice GIN.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| SQLite + FTS5 | Sem stemming de português. Também não aceita conexão de rede, o que forçaria a API a ser o único caminho de acesso remoto |
| SQLite agora, migrar depois | Migrar com dados reais é mais caro do que começar certo, e a decisão já estava tomada |

## Consequências

**Positivas.** Stemming de português nativo. Aceita conexão de rede, o que simplifica a Fase 9. Abre caminho para busca semântica com `pgvector` sem trocar de banco. Concorrência real, útil para o padrão banco-como-fila do worker (`FOR UPDATE SKIP LOCKED`).

**Negativas.** O sistema passa a depender de um serviço em execução: a interface desktop precisa tratar "banco fora do ar" como estado esperado, não como falha. Backup deixa de ser copiar um arquivo e vira rotina de `pg_dump` que precisa ser criada, agendada e **testada**. Um container a operar.

## Gatilho de reversão

Se a operação do container se mostrar um incômodo desproporcional ao ganho: por exemplo, se o Docker no WSL2 se revelar instável nesta máquina a ponto de atrapalhar o uso diário. Nesse caso, SQLite volta à mesa e a busca perde stemming, o que precisaria ser compensado de outra forma.
