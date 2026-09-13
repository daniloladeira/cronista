# ADR-0016 · Textual para navegação (list, ler, buscar)

- **Status:** revertido por [ADR-0017](0017-ink-para-navegacao.md)
- **Data:** 2026-08-17
- **Requisitos relacionados:** RP-06, RF-20 a RF-24 (UC-07, UC-08)
- **Reverte parcialmente:** [ADR-0015](0015-rich-como-apresentacao-cli.md)

> **Nota de 2026-09-04:** o gatilho de reversão deste ADR (ver seção própria, abaixo) disparou de novo — bugs de layout recorrentes no motor do Textual, não um problema pontual. Ver [ADR-0017](0017-ink-para-navegacao.md). `list`, `ler`, `buscar` e `devices` migraram pra Ink (`cronista-tui`) primeiro; no mesmo dia, o menu inicial (`cronista` sem comando, `home.py`) também migrou — ver nota no fim deste arquivo. Nada do que este ADR decidiu continua em produção; fica como registro de decisão, não como estado atual.

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

## Nota (2026-09-04): o gatilho de reversão disparou, pra `devices`

O próprio gatilho de reversão deste ADR previu isso: *"se o usuário frequentemente esquecer se um comando abre painel ou só imprime e sai — reconsiderar unificar tudo em um único modelo"*. Aconteceu de verdade — o usuário notou duas vezes, sem eu perguntar, que `cronista devices` "fechava sozinho" (imprimia e o processo terminava) e não parecia ter o mesmo design do resto (borda reta do Rich, sem a cor de identidade dourada que `list`/`ler`/`buscar` já usavam).

**Resposta, deliberadamente contida**: só `devices` absorvido pro modelo de tela persistente (`cronista/client/devices_screen.py`, `DevicesApp`), não uma reversão geral. `rec` continua fora de qualquer loop de evento — ADR-0006 protege isso especificamente por ser a única operação irreversível do sistema, e essa razão não mudou. `login`/`sync` não foram questionados, ficam como comandos que rodam e terminam até (se algum dia) o mesmo gatilho disparar pra eles.

Achado extra no caminho, mesma disciplina de sempre (exportar SVG antes de integrar): a primeira versão da tela colocava a `rich.Table` (com sua própria borda reta) dentro do painel Textual já arredondado — uma caixa dentro da outra. O usuário viu o resultado renderizado e apontou. Corrigido com `Table(box=None)`: só o painel externo emoldura, o conteúdo interno é texto alinhado, sem moldura própria.

## Nota (2026-09-04): o gatilho de reversão disparou de novo, desta vez pra valer — ver ADR-0017

A caixa-dentro-de-caixa do parágrafo acima não foi um incidente isolado: no mesmo dia, corrigindo o padding do título de `devices`, apareceu mais um bug de medição (`width: auto` do Textual não media a `rich.Table` dentro do `Static`, exigiu `width: 70` hardcoded que *mesmo assim* quebrava com nome de dispositivo comprido). Três bugs da mesma classe — motor de layout que não mede o próprio conteúdo direito — bateram um atrás do outro. O usuário relatou, sem eu perguntar: *"com o Rich eu estou tendo muitos problemas"*, e citou Ink como alternativa que "funciona muito melhor" para layout.

Isso é exatamente a pergunta que a tabela de alternativas deste ADR já tinha respondido "não" — *"Ink/TypeScript para as telas navegáveis: reabriria a discussão de dois runtimes, sem necessidade"*. A resposta mudou porque a premissa mudou: quando este ADR foi escrito, "Textual entrega a mesma capacidade de navegação" era verdade só sobre *capacidade*, não sobre *robustez de layout* — o padrão recorrente de bug não existia ainda como evidência.

**`list`, `ler`, `buscar` e `devices` migraram pra Ink** (`cronista-tui`, processo Node separado). Decisão completa, com alternativas e consequências negativas registradas, em [ADR-0017](0017-ink-para-navegacao.md).

## Nota (2026-09-04, mesmo dia): o menu inicial também migrou — `home.py` apagado de vez

O parágrafo acima considerou deixar o menu inicial (`home.py`) fora, por não ter o mesmo histórico de bug e por `cronista-tui` ainda não saber despachar pra `rec`/`sync`/`login`. Isso durou poucas horas: o usuário perguntou diretamente se a intenção era o Ink virar a porta única — "meio que o front", Python só onde precisa. A resposta era sim, e a segunda razão (não saber despachar) deixou de ser motivo pra não fazer, virou trabalho a fazer: `cronista-tui` ganhou três itens de sidebar (Gravar/Sincronizar/Login) que saem do Ink e rodam `cronista <sub>` como processo Python à parte, sentido inverso do mecanismo que já existia.

Com isso, **nenhuma tela deste ADR continua em pé** — `list`, `ler`, `buscar`, `devices` e agora o menu inicial migraram todos pra `cronista-tui`. Este ADR fica só como registro histórico da decisão original (por que Textual entrou, por que fazia sentido em 2026-08-17), não como estado atual do sistema. Detalhe completo da migração final em [ADR-0017](0017-ink-para-navegacao.md) (nota "o menu inicial também migrou").
