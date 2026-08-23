-- Busca em português de verdade, em duas camadas (docs/15-roadmap.md,
-- Fase 5 -- medido, não presumido, cada linha abaixo corrige algo que
-- foi testado e falhou com o dicionário 'portuguese' padrão):
--
-- 1. hunspell (ispell, lista de palavras real) ANTES do snowball --
--    resolve flexão irregular que o snowball sozinho não pega, como
--    "decisão"/"decisões" (plural em -ão/-ões).
-- 2. sinônimos ANTES do hunspell -- resolve derivação (substantivo
--    formado a partir de verbo) que nem hunspell nem snowball tratam,
--    como "decisão"/"decidimos": mapeia o substantivo pro verbo, que já
--    reduz certo sozinho.
--
-- Só roda automaticamente na primeira inicialização de um volume vazio
-- (padrão do docker-entrypoint do Postgres, mesmo aviso de
-- 01-create-test-db.sql). Para um volume já existente, roda-se essa
-- mesma criação uma vez à mão, contra cada banco.
--
-- Precisa vir DEPOIS de 01-create-test-db.sql (ordem lexical do
-- entrypoint) -- \c cronista_test abaixo depende do banco já existir.
CREATE TEXT SEARCH DICTIONARY pt_br_hunspell (
    TEMPLATE = ispell,
    DictFile = pt_br,
    AffFile = pt_br,
    StopWords = portuguese
);

CREATE TEXT SEARCH DICTIONARY pt_br_sinonimos (
    TEMPLATE = synonym,
    SYNONYMS = pt_br_sinonimos
);

CREATE TEXT SEARCH CONFIGURATION pt_br_hunspell (COPY = portuguese);

ALTER TEXT SEARCH CONFIGURATION pt_br_hunspell
    ALTER MAPPING FOR word, hword, hword_part, asciiword, hword_asciipart, asciihword
    WITH pt_br_sinonimos, pt_br_hunspell, portuguese_stem;

\c cronista_test

CREATE TEXT SEARCH DICTIONARY pt_br_hunspell (
    TEMPLATE = ispell,
    DictFile = pt_br,
    AffFile = pt_br,
    StopWords = portuguese
);

CREATE TEXT SEARCH DICTIONARY pt_br_sinonimos (
    TEMPLATE = synonym,
    SYNONYMS = pt_br_sinonimos
);

CREATE TEXT SEARCH CONFIGURATION pt_br_hunspell (COPY = portuguese);

ALTER TEXT SEARCH CONFIGURATION pt_br_hunspell
    ALTER MAPPING FOR word, hword, hword_part, asciiword, hword_asciipart, asciihword
    WITH pt_br_sinonimos, pt_br_hunspell, portuguese_stem;
