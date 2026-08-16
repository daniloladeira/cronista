# ADR-0007 · Fonte de áudio plugável

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** RF-09, RN-02

## Contexto

A gravação ao vivo era o único caminho previsto. O usuário manifestou depois a intenção de também importar arquivos de áudio já existentes — "mas isso é pra depois".

O ponto: **adiar a implementação é barato; adiar a abstração não é.** Se o modelo de dados e o pipeline forem escritos presumindo captura ao vivo, a importação depois exige migração de esquema com dados reais e reescrita do pipeline.

Três coisas quebrariam: `meetings` sem indicação de origem; falante como enumeração de dois valores (`voce`, `outros`), sem lugar para arquivo de trilha única; e pipeline recebendo exatamente duas trilhas.

## Decisão

Abstrair a fonte de áudio **desde a primeira versão**, mesmo com a importação implementada só na Fase 6:

1. `meetings.source` com valores `capture` e `import`.
2. `speaker` como texto livre, não enumeração — abre espaço para `desconhecido` e para identificação nominal futura.
3. Pipeline de transcrição operando sobre uma **lista** de trilhas, de tamanho variável.
4. Entidade `Track` própria, em vez de colunas fixas `mic_path` e `system_path`.

## Consequências

**Positivas.** A Fase 6 vira conversão de formato mais um `POST` no endpoint que a Fase 2 já constrói. Nenhuma migração de esquema. Gravação e importação convergem em UC-10, o que o modelo de casos de uso tornou explícito.

**Negativas.** Complexidade ligeiramente maior desde o início: uma tabela a mais e um laço onde caberiam duas variáveis. Custo real, mas pequeno, e pago uma vez.

**Não resolvido.** Arquivo importado tem trilha única e, portanto, falante `desconhecido`. A separação por origem de sinal — o truque que dispensa diarização no ADR-0001 — não existe aqui.

## Gatilho de reversão

Não há reversão a considerar. A questão em aberto é outra: **se a ausência de falante em arquivos importados prejudicar a qualidade do resumo**, diarização entra apenas neste caminho. A decisão fica para a Fase 6, com evidência real, e a recomendação é começar por `desconhecido` e só pagar o custo se o resumo sofrer.
