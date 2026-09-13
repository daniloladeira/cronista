# ADR-0017 · Ink para navegação, substituindo Textual (list, ler, buscar, devices)

- **Status:** aceito
- **Data:** 2026-09-04
- **Requisitos relacionados:** RP-06, RF-20 a RF-24 (UC-07, UC-08), UC-02
- **Reverte parcialmente:** [ADR-0016](0016-textual-para-navegacao.md)

## Contexto

O [ADR-0016](0016-textual-para-navegacao.md) escolheu Textual sobre Ink para as telas navegáveis, com uma razão explícita de descartar Ink: *"reabriria a discussão de dois runtimes, sem necessidade — Textual entrega a mesma capacidade de navegação, em Python, sem fronteira nova."* Isso continuou verdadeiro sobre *capacidade*. Não continuou verdadeiro sobre *robustez de layout*.

No mesmo dia em que esse ADR foi revisitado, três bugs da mesma classe apareceram em sequência, todos em `devices_screen.py`: caixa dentro de caixa (uma `rich.Table` com borda própria dentro do painel Textual já arredondado), `width: auto` do Textual não medindo o conteúdo real de um `Static` contendo uma tabela Rich (exigiu `width: 70` hardcoded), e mesmo com esse número fixo, um nome de dispositivo comprido ainda quebrava em duas linhas dentro da largura fixa. Antes disso, a primeira tentativa de menu navegável (`home.py`) já tinha sido descartada uma vez por ficar "horrível, horrível, horrível" visualmente (nota de 2026-08-18 no ADR-0016). O padrão não é um bug pontual — é o motor de layout do Textual não medindo o próprio conteúdo de forma confiável quando o conteúdo vem de outro lugar (uma `rich.Table`, um `Text` multi-linha).

O usuário relatou, sem eu perguntar: *"com o Rich eu estou tendo muitos problemas"*, e apontou Ink como alternativa — *"todo o layout funciona muito melhor no ink"*. Como verificação, não só opinião: recriei a tela `devices` num protótipo Ink isolado, com o mesmo dado real (mesmo nome de dispositivo comprido que quebrava no Textual) — sem nenhuma largura hardcoded, o painel Ink cresceu certo pro conteúdo. O protótipo em si reproduziu, à toa, a mesma classe de erro (larguras calculadas errado) até eu ler código de um CLI real em Ink ([torlink](https://github.com/baairon/torlink), MIT) e adotar os padrões de lá — registrado em detalhe em `cronista-tui/README.md`, não repetido aqui.

## Decisão

**Ink** (React pra terminal, Node.js) para as telas de navegação: `list`, `ler`, `buscar` e `devices` migram pra `cronista-tui`, um processo Node separado que fala com a mesma API e o mesmo arquivo de token que o cliente Python já usa (`%LOCALAPPDATA%\cronista\auth.json`) — sessão compartilhada, não duplicada.

`cli.py` (Python/Typer) chama `cronista-tui` via subprocess (`cronista/client/cronista_tui.py`), passando a seção/reunião/termo de busca inicial por variável de ambiente, e herda o terminal do processo pai (o app usa modo raw de teclado, não dá pra rodar num pipe).

`rec`, `login`, `sync` e `importar` **continuam exatamente como estão**: comandos Python que rodam e terminam, decorados com Rich (ADR-0015 continua valendo pra eles). O menu inicial (`cronista` sem comando, `home.py`) **também continua Textual** — não tem o mesmo histórico de bug de layout que motivou esta troca, e hoje despacha pra `rec`/`sync`/`login`, que `cronista-tui` não sabe abrir.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Continuar em Textual, corrigir cada bug de largura conforme aparece | Era o caminho seguido até aqui (ADR-0016) — cada correção revelou outro bug da mesma classe (medição de conteúdo), não um caso isolado. Terceiro bug no mesmo dia é padrão, não acidente |
| Migrar o CLI inteiro pra Ink/Node, incluindo `rec`/`login`/`sync` | `rec` é a única operação irreversível do sistema (ADR-0006/0012); trazer um runtime novo pro caminho de maior risco não tem benefício que compense. `login`/`sync` não têm histórico de bug de layout — não há problema a resolver aí |
| Migrar só `devices` (o pior ofensor), deixar `list`/`ler`/`buscar` em Textual | Pior dos dois mundos: duas telas de navegação com motor de layout diferente, inconsistência visual entre elas — exatamente o tipo de confusão que o gatilho de reversão do ADR-0016 já citava como risco |

## Consequências

**Positivas.** Yoga (motor de layout do Ink, baseado em Flexbox) mede largura de conteúdo real — testado lado a lado contra o mesmo bug que motivou a troca (nome de dispositivo comprido): sem nenhuma largura hardcoded, o painel cresce certo. Ecossistema Ink tem exemplo real pra copiar padrão (torlink), o que já rendeu correções concretas (largura com piso/teto vinda do terminal, não do conteúdo; coluna flexível que trunca em vez de crescer sem limite). `Escape` agora sobe um nível de cada vez entre detalhe→lista→sidebar→home, incluindo trocar de `devices` pra `list` sem sair do programa — capacidade que não existia antes (cada tela Textual era estanque).

**Negativas.** Dois runtimes agora, não um — `cronista-tui` exige Node.js instalado além de Python, mais uma dependência de ambiente. Processo separado via subprocess, não mais um import direto: perde-se acesso direto ao estado do processo Python (contornado com variáveis de ambiente pra passar seção/reunião/termo inicial, funcional mas mais rígido que uma chamada de função). `cronista-tui` também não chegou sem os mesmos tipos de bug que motivaram a saída do Textual — um off-by-one na largura da borda do painel e a largura da sidebar não contando a própria margem, ambos achados e corrigidos durante a migração (`cronista-tui/README.md`), o que é evidência de que "usar Yoga" não é bala de prata sozinho, exige a mesma disciplina de medir e não presumir. Resumo de reunião (markdown) renderiza como texto puro por enquanto — Ink não tem um widget `Markdown` pronto como o Textual tinha, essa fidelidade visual foi perdida na migração.

## Gatilho de reversão

Se `cronista-tui` (processo Node separado, subprocess a partir do Python) se provar mais frágil na prática do que os bugs de layout do Textual que motivaram a troca — por exemplo, spawn de subprocess falhando de formas imprevisíveis entre máquinas, ou a sincronização de token entre os dois processos dando problema de verdade em uso real — reconsiderar. Nesse caso, a pergunta não é só "voltar pro Textual", é também perguntar se a fronteira de processo (não a escolha de motor de layout) foi o erro.

## Nota (2026-09-04, mesmo dia): abrir reunião e busca

`ler`/`buscar` (transcrição+resumo com abas, busca com repopulação da lista) foram portados pro `cronista-tui` antes de apagar `panel.py` — decisão explícita do usuário, escolhida entre três opções (apagar tudo já aceitando a lacuna, portar tudo antes de apagar, ou manter os dois lados vivos por mais tempo). Só depois disso `devices_screen.py` e `panel.py` foram removidos de fato, sem lacuna de funcionalidade. Detalhe técnico (o handler de `Escape` que precisou ser reestruturado por tela, não global) em `cronista-tui/README.md`.

## Nota (2026-09-04, mesmo dia): o menu inicial também migrou -- `home.py` apagado

A seção **Decisão**, acima, dizia que o menu inicial "também continua Textual", porque não tinha o mesmo histórico de bug e porque `cronista-tui` não sabia despachar pra `rec`/`sync`/`login`. Essa segunda razão deixou de valer: o usuário perguntou diretamente se a ideia era "o Ink ser meio que o front, o que precisa de Python mantém" — confirmando que o objetivo é porta única, não duas telas iniciais diferentes (Textual pra escolher comando, Ink só pra navegar depois de escolher).

**`home.py` foi apagado.** `cronista` sem comando agora abre o `cronista-tui` direto (`cronista_tui.run()`, sem `section`), que mostra o banner e uma sidebar de 5 itens: Reuniões/Dispositivos (ficam em Ink, como já estava) e **Gravar/Sincronizar/Login**, novos, que saem do Ink e rodam `cronista <sub>` como processo Python à parte (`cronista-tui/src/pythonBridge.js`) -- o inverso exato do mecanismo que `cronista_tui.py` já tinha, agora nos dois sentidos.

A garantia do ADR-0006 continua de pé, e é isso que faz este design seguro: a captura de áudio em si **nunca** roda dentro do Node, nem passa por ele — `pythonBridge.js` só decide *quando* chamar `cronista rec`, o próprio comando roda 100% Python, exatamente como sempre rodou. O que mudou foi só *quem mostra o menu que leva até lá*.

**Cuidado técnico que não existia antes de ter dois processos disputando o terminal**: o Node só pode chamar o Python depois que o Ink desmontou de vez e devolveu o modo raw do stdin — chamar antes corromperia o terminal. `index.js` resolve isso com `await waitUntilExit()` antes de spawnar, ver `cronista-tui/README.md`.

`importar` não entrou no menu — precisa de um caminho de arquivo obrigatório, não cabe num seletor de seta (mesma limitação que já valia pro `home.py` original).
