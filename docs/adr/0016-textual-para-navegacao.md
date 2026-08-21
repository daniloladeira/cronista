# ADR-0016 · Textual para navegação (list, ler, buscar)

- **Status:** aceito
- **Data:** 2026-08-17
- **Requisitos relacionados:** RP-06, RF-20 a RF-24 (UC-07, UC-08)
- **Reverte parcialmente:** [ADR-0015](0015-rich-como-apresentacao-cli.md)

## Contexto

O [ADR-0015](0015-rich-como-apresentacao-cli.md) escolheu Rich sobre Textual para todo o CLI, com um gatilho de reversão explícito: *"se o modelo 'comando roda e termina' se mostrar insuficiente para o que o usuário efetivamente quer no uso diário, por exemplo desejar navegação persistente... Textual volta à mesa."*

Esse gatilho disparou. Ao ver referências de apps de terminal navegáveis (torlink, o próprio Claude Code), o usuário identificou uma vontade concreta: navegar pela lista de reuniões, ler transcrição e resumo trocando de aba sem novo comando, e percorrer resultado de busca — não apenas ler uma tabela impressa e digitar outro comando pra cada passo.

Perguntado especificamente **onde** essa navegação deveria existir, a resposta excluiu a gravação: o usuário quer navegar em `list`, `ler` e `buscar` (UC-07, UC-08), não durante o `rec` (UC-03). Isso é decisivo. A razão original do ADR-0006 — não misturar a captura, única operação irreversível do sistema, com a complexidade de um loop de evento — continua de pé, porque a captura não é onde a navegação foi pedida.

## Decisão

**Textual** para as telas de navegação: `list`, `ler` e `buscar` convergem numa experiência de terminal persistente e navegável — provavelmente um único comando que abre um painel (lista à esquerda ou acima, leitura de transcrição/resumo com abas, busca embutida), não três comandos que rodam e terminam.

`rec`, `login`, `devices`, `importar` e `sync` **continuam exatamente como especificado**: comandos que rodam e terminam, decorados com Rich (ADR-0015 permanece válido para eles). A gravação não entra em loop de evento algum.

**Continua Python.** Textual é da mesma equipe do Rich (Textualize), roda no mesmo processo, importa direto o cliente HTTP e a autenticação já construídos — sem runtime novo, sem fronteira de processo, sem o custo de migração que foi avaliado e descartado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Manter tudo em Rich, sem navegação | É a opção que o próprio usuário rejeitou ao pedir navegação explicitamente |
| Ink/TypeScript para as telas navegáveis | Reabriria a discussão de dois runtimes, sem necessidade — Textual entrega a mesma capacidade de navegação, em Python, sem fronteira nova. Ver conversa registrada nesta sessão sobre migração |
| Textual para o CLI inteiro, incluindo `rec` | Reabriria o risco que o ADR-0006 evitou. O usuário especificamente não pediu isso |

## Consequências

**Positivas.** A navegação que o usuário quer passa a ter o framework certo, não uma simulação forçada em Rich. Zero custo de runtime adicional. `rec` continua simples e protegido.

**Negativas.** O CLI passa a ter **dois modelos de interação simultâneos**: comandos que rodam e terminam (maioria) e uma experiência persistente e navegável (para consulta). Isso precisa ficar claro na documentação — [11-cli.md](../11-cli.md) e [17-identidade-visual-cli.md](../17-identidade-visual-cli.md) — para não confundir qual comando faz o quê. Mais uma dependência (`textual`), mais superfície de teste (navegação por teclado, foco, estado da tela).

## Gatilho de reversão

Se, na prática, a divisão dois-modelos-de-interação confundir mais do que ajudar — por exemplo, se o usuário frequentemente esquecer se um comando abre painel ou só imprime e sai — reconsiderar unificar tudo em um único modelo, provavelmente absorvendo os comandos simples para dentro do painel Textual também.

## Nota

Esta decisão é de escopo (Fase 5 — Busca e leitura, UC-07/UC-08), registrada agora porque a conversa que a motivou aconteceu agora. Implementação fica para quando a Fase 5 chegar; o projeto ainda está na Fase 2.

## Nota (2026-08-18)

Uma tentativa de estender este ADR pro menu inicial (`cronista` sem comando ficar navegável, Textual) foi implementada e revertida no mesmo dia — o resultado visual não ficou bom (testado de verdade, não só decidido em teoria) e foi descartado antes de virar commit. `cronista` sem comando continua mostrando o banner (docs/17 §7) seguido da ajuda do Typer, como já era. Fica registrado que a ideia foi tentada e por quê não vingou desta vez, caso volte à mesa: a lição foi entregar um preview de verdade (screenshot/export) antes de ligar qualquer coisa nova ao CLI real, não só descrever em texto.

## Nota (2026-08-19): segunda tentativa, funcionou

O menu inicial navegável (`cronista/client/home.py`, `HomeApp`) foi refeito e desta vez ficou de pé. A diferença: preview de verdade antes de integrar, via `App.export_screenshot()` do próprio Textual (SVG, comparado linha por linha por script, não só olhado por cima) — não uma captura de tela manual pedida ao usuário. Dois bugs reais foram achados e corrigidos **antes** de qualquer coisa chegar no `cli.py`:

1. **Banner cortado no meio de cada linha.** O `Static` não reservava largura suficiente pra uma `Text` de 63+ caracteres com quebras de linha internas; `width: auto` do Textual não mede direito esse caso. Corrigido com `no_wrap=True` + `overflow="ignore"` na `Text` do banner e uma largura explícita no `Static` (`banner.width() + 2`).
2. **Fundo preto (`#121212`) onde antes não tinha nenhum.** Era o tema escuro padrão do Textual, que pinta a tela inteira — diferente do resto do app, que só imprime, sem fundo próprio. Corrigido com `App(ansi_color=True)`, que usa a paleta/fundo do terminal real em vez do tema fixo.

`session_info.py` foi extraído pra conteúdo (banner, subtítulo, categorias, usuário/máquina) compartilhado entre o menu navegável e o fallback estático (fora de terminal interativo) — as duas telas mostram o mesmo texto, só a lista de comandos embaixo muda de forma.
