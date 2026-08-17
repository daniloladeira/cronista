-- Banco separado para testes automatizados, no mesmo container de
-- desenvolvimento. Ver docs/14-plano-de-testes.md §7.
--
-- Só roda automaticamente na primeira inicialização de um volume vazio
-- (padrão do docker-entrypoint do Postgres). Para um volume já existente,
-- rode manualmente uma vez:
--   docker exec -it cronista-db psql -U cronista -d postgres \
--     -c "CREATE DATABASE cronista_test;"
CREATE DATABASE cronista_test;
