# Postgres + dicionário hunspell de português, encadeado antes do
# stemmer snowball padrão. Achado testando de verdade: o dicionário
# 'portuguese' (snowball, por sufixo) não junta "decisão"/"decisões"
# (plural irregular -ão/-ões) nem "decisão"/"decidimos" (substantivo/
# verbo) -- CT-27 e docs/08-modelo-de-dados.md dependem disso funcionar
# de verdade. Ver docs/15-roadmap.md, Fase 5.
FROM postgres:17-alpine

# hunspell-pt-br instala pt_BR.dic/pt_BR.aff em /usr/share/hunspell/,
# em ISO-8859-1 (declarado na linha "SET ISO8859-1" do .aff). O Postgres
# NÃO converte sozinho a partir dessa linha -- testado de verdade, deu
# "invalid byte sequence for encoding UTF8" lendo o .dict direto. Precisa
# converter os dois arquivos pra UTF-8 e corrigir a linha SET, senão o
# Postgres tenta converter de novo um arquivo que já está em UTF-8.
# tsearch_data/ também espera extensão .dict/.affix, não .dic/.aff.
RUN apk add --no-cache hunspell-pt-br \
    && iconv -f ISO-8859-1 -t UTF-8 /usr/share/hunspell/pt_BR.dic \
        > /usr/local/share/postgresql/tsearch_data/pt_br.dict \
    && iconv -f ISO-8859-1 -t UTF-8 /usr/share/hunspell/pt_BR.aff \
        | sed 's/^SET ISO8859-1/SET UTF-8/' \
        > /usr/local/share/postgresql/tsearch_data/pt_br.affix

# Sinônimos que unem substantivo/verbo derivacionalmente relacionados
# (docs/15-roadmap.md, Fase 5) -- nem snowball nem hunspell fazem isso
# sozinhos, só flexão (plural, conjugação).
COPY tsearch_data/pt_br_sinonimos.syn /usr/local/share/postgresql/tsearch_data/pt_br_sinonimos.syn
