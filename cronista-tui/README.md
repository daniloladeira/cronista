# cronista-tui

Porta de entrada única do `cronista` em Ink (React pra terminal) —
sucessora de `cronista/client/home.py`, `panel.py` e `devices_screen.py`
(todos apagados). Motivo da troca: histórico real de bugs de layout no
lado Rich/Textual (caixa dentro de caixa, `width` hardcoded que ainda assim
quebrava com nome de dispositivo longo, primeira versão de Textual
rejeitada como "horrível, horrível, horrível" — ver
[ADR-0016](../docs/adr/0016-textual-para-navegacao.md) e
[ADR-0017](../docs/adr/0017-ink-para-navegacao.md)).

## O que fica em cada lado

`cronista` (sem comando) abre **este** app -- não existem mais duas
portas de entrada diferentes. A partir daqui, cada item da sidebar decide
se fica em Ink ou volta pro Python:

| Item | Onde roda | Por quê |
|---|---|---|
| Reuniões (`list`/`ler`/`buscar`) | Ink, tela persistente | Navegação de verdade -- é o motivo original da migração |
| Dispositivos | Ink, tela persistente | Mesmo motivo; dado real vem do Python via `devices.py` (`capture.py`/`soundcard`, só Python fala WASAPI) |
| Gravar (`rec`) | **Python**, `cronista-tui` sai antes de rodar | Único lugar com risco real de perda de dado (ADR-0006/0012) -- não entra em runtime concorrente nenhum, de propósito |
| Sincronizar (`sync`), Login | **Python**, `cronista-tui` sai antes de rodar | Comando roda e termina, sem navegação -- não tem tela pra migrar |

`devices.py`, na raiz deste pacote, é a ponte Python→Node: chama
`cronista.client.capture.list_input_devices()/list_output_devices()` e
devolve JSON. Dado real desta máquina, nunca fixture inventada.

`pythonBridge.js` é a ponte Node→Python: sentido contrário, pra "Gravar"/
"Sincronizar"/"Login" (ver seção própria, abaixo). `importar` não está no
menu -- precisa de um caminho de arquivo obrigatório, não cabe num
seletor de seta (mesma razão que já valia pro `home.py` antigo).

## Rodar

```bash
npm install
npm start            # app interativo real, precisa de terminal TTY (q sai, Enter abre o menu)
npm run capture       # captura estática (Home + as duas seções), sem TTY -- pra inspecionar layout
```

**Sessão compartilhada com o Python**: `apiClient.js` lê o mesmo
`%LOCALAPPDATA%\cronista\auth.json` que `cronista/client/token_store.py`
escreve — faça `cronista login` (lado Python) antes de abrir "Reuniões"
aqui. Sem token, a tela mostra "Não autenticado. Rode `cronista login`."
em vez de travar ou mostrar traceback (mesmo padrão de clareza que
`panel.py` já seguia, RNF-U02).

## Estrutura

```
src/
  theme.js         paleta (docs/17-identidade-visual-cli.md §4) -- não inventar cor nova aqui
  constants.js      parâmetros do shimmer, iguais em toda tela
  shimmer.js        porta 1:1 de cronista/client/colors.py
  Rule.js           régua horizontal, largura sempre vem de fora
  Panel.js          painel com título na borda (Ink não tem título nativo de borda)
  DeviceTable.js    tabela nome/padrão pra Dispositivos
  MeetingList.js    lista selecionável pra Reuniões
  MeetingDetail.js  transcrição/resumo de uma reunião aberta (abas + rolagem)
  ScrollText.js     janela de rolagem manual (Ink não tem painel com scroll nativo)
  TextInput.js      campo de texto simples, usado pela busca
  Notice.js         aviso inline temporário (equivalente ao toast do Textual)
  Banner.js         banner grande com degradê, FIGlet "ANSI Compact"
  apiClient.js      porta mínima de api_client.py + token_store.py (GET autenticado)
  pythonBridge.js   spawna `cronista <sub>` (Python) quando um item "launch" é escolhido
  App.js            estado: view (home/main), cursor/section (o que a sidebar destaca vs. mostra), region (sidebar/content)
  index.js          monta o Ink, espera desmontar de vez, só então spawna Python (se pedido)
  screens/
    Home.js         tela inicial centralizada
    Header.js        cabeçalho pequeno (fora da home) -- título + régua de ponta a ponta
    Sidebar.js       navegação lateral (2 seções Ink + 3 lançadores Python)
    Devices.js       conteúdo da seção Dispositivos
    Meetings.js      conteúdo da seção Reuniões (lista/detalhe/busca)
```

## Padrões que vieram de olhar código Ink real

Depois do primeiro spike (agora removido, as lições ficaram aqui) ter
reinventado alguns problemas do Rich em vez de resolvê-los, fui ler
[torlink](https://github.com/baairon/torlink) (MIT), um CLI real em Ink.
Três coisas de lá que valem a pena registrar, porque não são óbvias:

1. **Largura vem do terminal, com piso e teto — nunca do conteúdo.**
   `App.tsx` do torlink: `Math.max(24, Math.min(cols - 4, 62))`. A
   primeira versão daqui calculava a largura do painel de Dispositivos
   pelo nome de dispositivo mais longo — parecia resolver o `width: 70`
   hardcoded do Rich, mas era o mesmo tipo de gambiarra ao contrário: sem
   teto, estourava a linha do terminal de verdade (visto rodando `npm
   start` num terminal de 80 colunas). `App.js::contentWidth()` e
   `Home.js` seguem a fórmula do torlink.

2. **Coluna flexível trunca, não cresce.** `Results.tsx` do torlink:
   `<Box flexGrow={1} minWidth={0}><Text wrap="truncate-end">`. Sem
   `minWidth={0}`, Yoga não deixa o item flexível encolher abaixo do
   próprio conteúdo — é a causa raiz do item 1. `DeviceTable.js` e
   `MeetingList.js` usam o mesmo par de props.

3. **Centralização de verdade é `justifyContent`/`alignItems: "center"`
   num `Box` do tamanho do terminal**, não padding calculado à mão —
   `Splash.tsx` do torlink. `home.py` (Python/Textual) tentou
   centralizar uma vez e comentou no próprio código que "quebrou de
   verdade no terminal do usuário"; `Home.js` usa a técnica do torlink.

**Dois bugs de largura que eu mesmo introduzi, achados rodando `npm run
capture` e olhando a saída de verdade (mesmo método do ADR-0016, não
comparação por opinião):**

- `Panel.js`: o cálculo do preenchimento da borda de cima errava por 1
  caractere (`w - title.length - 4`, devia ser `-5`) — estourava a
  largura do `Box` em exatamente 1 coluna e o Ink quebrava a linha
  silenciosamente, virando uma linha em branco fantasma entre o topo e o
  corpo do painel.
- `Sidebar.js`: `SIDEBAR_WIDTH` (usado por `App.js` pra calcular a
  largura do conteúdo ao lado) não contava a própria `marginRight` da
  sidebar — a soma estourava por exatamente essas 2 colunas e quebrava a
  borda do painel de conteúdo, mesma classe de bug do item anterior.
  Corrigido separando largura própria (`_INNER_WIDTH`) de rodapé total
  (`SIDEBAR_WIDTH = _INNER_WIDTH + _MARGIN_RIGHT`).

## Banner grande

`Banner.js` porta a técnica de `cronista/client/banner.py::_sheen/_big`
pra Ink -- degradê por caractere numa grade 2D (linha × coluna), mesmas 5
paradas de cor (`#FFFFFF → #F7ECDA → #DFB878 → #C9A968 → #B8934F`), estático
(sem sweep -- a animação de brilho é só do cabeçalho pequeno, docs/17 §7
separa os dois). Fonte trocada de "ANSI Shadow" (a que o Python usa, 7
linhas de altura) pra "ANSI Compact" (3 linhas) -- mesma família FIGlet,
pedido explícito do usuário pra ficar menor. `Home.js` mostra o banner
grande se o terminal couber (`columns >= bannerWidth + 2`, mesmo critério
de `banner.py::render()` e de `Splash.tsx` do torlink), senão cai pro
nome pequeno com shimmer que já existia.

**Não verificado visualmente nesta sessão**: `ink-testing-library` (usado
por `npm run capture`) reporta cor desligada pro chalk por trás — a
captura estática nunca mostra o degradê de verdade, só a forma das letras.
Cor só se confirma com `npm start` num terminal truecolor de verdade.

## Alertas (`self.notify` do Textual)

`panel.py` tinha três `self.notify(str(exc), title="Erro", severity="error",
timeout=8)` — um toast que aparece, some sozinho em 8s, e **não apaga o que
já estava na tela por baixo**. A primeira versão daqui não tinha
equivalente: erro substituía o painel inteiro (achado o gap porque o
usuário perguntou se os alertas tinham sumido — tinham). Corrigido com
`Notice.js`: mensagem inline no topo do painel, desaparece sozinha depois
de `timeoutMs` (8000 por padrão, casando com o original), e o estado da
lista (`meetings`) fica separado do estado do aviso — um erro numa busca
futura não vai mais poder apagar a lista que já estava carregada. Ink não
tem overlay flutuante nativo como o Textual; o princípio (temporário, não
destrutivo) é o mesmo, a apresentação (inline, não flutuante) não é.

Portado pras três operações que existem hoje (`_carregar_lista`,
`_buscar`, `_abrir_reuniao` viraram `listMeetings`/`search`/`getMeeting`+
`getTranscript` em `apiClient.js`) -- cada uma usa `Notice.js`, nenhuma
mais derruba o painel inteiro num erro.

## Abrir reunião e busca (`ler`/`buscar` de `panel.py`)

`Meetings.js` agora tem três modos (`list`/`detail`/`search`), um
`useInput` ativo por modo -- mesma disciplina de `Results.tsx` do torlink
(`isActive: focused && mode === "list"`, etc.), pra não ter dois handlers
competindo pela mesma tecla.

- **Enter** numa reunião da lista abre `MeetingDetail.js`: abas
  Transcrição/Resumo (`Tab` troca), rolagem manual em `ScrollText.js`
  (`↑↓`/`PageUp`/`PageDown` -- Ink não tem painel com scroll nativo tipo
  o `VerticalScroll` do Textual, janela de `VIEWPORT_HEIGHT` linhas
  calculada à mão).
- **`/`** abre `TextInput.js` (campo de busca simples, sem lib -- Ink não
  tem input pronto no projeto), Enter busca e repopula a lista com o
  mesmo formato de `panel.py::_buscar` (agrupado por reunião, trecho como
  "status").
- **Escape** sobe um nível por vez: detalhe → lista → sidebar → home.
  Isso exigiu tirar o `Escape` do handler global de `App.js` -- um
  handler fixo lá em cima competia com o handler local da tela de
  detalhe, os dois reagindo ao mesmo Escape ao mesmo tempo (achado real
  montando a tela: pulava detalhe→lista E lista→sidebar juntos). Agora
  `App.js` só cuida de "q" e do Enter que sai da home; cada tela decide
  se Escape é dela ou se chama o `onBack` que o pai passou.

**Resumo em markdown vira texto puro** (`latestSummaryLines` em
`MeetingDetail.js`) -- sem negrito de cabeçalho nem lista com marcador
estilizado, ao contrário do widget `Markdown` que o Textual tinha pronto.
Ink não tem equivalente nativo; dava pra trazer `marked`/`marked-terminal`
depois se isso incomodar de verdade.

## Menu unificado: sair do Ink pra rodar Python (ADR-0017)

`cronista` sem comando não abre mais `home.py` -- abre este app direto,
com banner + sidebar de 5 itens: Reuniões/Dispositivos (Ink, como sempre)
e Gravar/Sincronizar/Login (Python). É o sentido contrário de
`cronista_tui.py` (Python spawnando Node): aqui é `pythonBridge.js` que
spawna `<repo>/.venv/Scripts/cronista.exe <sub>`, herdando o terminal
inteiro (`stdio: "inherit"`).

**Sequência importa.** `index.js` só chama `launchPython()` **depois** de
`await waitUntilExit()` resolver -- ou seja, depois do Ink desmontar de
vez e devolver o modo raw do terminal. `App.js` passa a intenção
("gravar"/"sincronizar"/"login") por uma callback (`onLaunch`) até
`index.js`, que guarda numa variável e só spawna fora da árvore do React,
depois do `render()` ter terminado de verdade. Chamar o Python **antes**
do Ink soltar o terminal corromperia o modo raw -- os dois processos
disputando o mesmo stdin ao mesmo tempo.

**Cursor da sidebar e seção mostrada são estados separados** (`cursorItem`
vs `section` em `App.js`): passar a seta por cima de "Gravar" não pode
trocar escondido o painel de Reuniões pro de Dispositivos. Só um item
"section" (Reuniões/Dispositivos) atualiza `section`; um item "launch"
troca só o texto de dica no painel de conteúdo (`cronista rec -- grava
até Ctrl+C, sai do Ink`), sem mexer em qual seção fica "lembrada".

**Verificado**: o spawn em si (`spawnSync` com `stdio: "inherit"`, testado
chamando `cronista.exe --help` de dentro do Node -- saída aparece
corretamente, código de saída 0), e a navegação até o item de lançamento
(`Sidebar.js` isolado, seta até "Gravar" + Enter chama `onLaunch` com o
item certo -- testado com `ink-testing-library`). **Não verificado**: a
troca de modo raw de verdade dentro do fluxo completo (escolher "Gravar"
no menu Ink de pé, confirmar que `cronista rec` assume o terminal limpo,
sem lixo visual) -- exige um terminal interativo de verdade, que esta
sessão não tem.

**Depois de `rec`/`sync`/`login` terminar, o cronista-tui volta -- não
fecha de vez.** `index.js` sai do Ink, roda o Python, e quando ele
termina volta pro Ink já em "Reuniões" -- pedido do usuário, pra ver a
reunião recém-gravada na lista sem digitar `cronista list` de novo. "q"
dentro do Ink, sem escolher nenhum lançador, é a saída final. A "volta"
NÃO é outro `render()` no mesmo processo (ver seção abaixo, "três
versões até acertar") -- é `index.js` chamando a si mesmo como processo
Node novo (`spawnSync(process.execPath, [__filename], ...)`), com
`CRONISTA_TUI_SECTION=reunioes` no ambiente. Por isso
`initialSection`/`initialMeetingId`/`initialSearchTerm` são prop do
`App`, lidas do `process.env` só em `index.js` -- cada processo lê a sua
cópia, nenhum componente é montado duas vezes no mesmo processo.

`importar` continua fora do menu (precisa de argumento obrigatório).
`login` reaproveita o prompt que o próprio comando Python já tem
(`typer.Option(..., prompt=True)`) -- nenhuma lógica de prompt nova no
lado Node.

## Header duplicado na troca home↔main

Achado real, reportado pelo usuário via print: depois de apertar Enter na
home, o cabeçalho pequeno ("cronista" + régua) aparecia **duas vezes**
empilhado. Causa: Ink não usa tela alternada (`alt-screen`) por padrão —
a saída da tela anterior fica no scrollback do terminal até algo mandar
limpar de verdade; o diff incremental de frame (que normalmente só
reescreve o que mudou) não é garantia suficiente numa troca de tela
inteira (Home, centralizada, pro layout principal, com sidebar).

Corrigido com `clear()`, retornado por `render()` (`index.js`) -- chamado
explicitamente nas duas transições (`App.js::goHome`/`goMain`) antes de
trocar `view`. `clear` só existe depois de `render()` já ter rodado, mas
o `App` precisa dele como prop na própria criação — resolvido com uma
variável indireta (`clearFn`) reatribuída logo depois do `render()`.

## Timeout no `apiClient.js` -- achado real, gravação de teste demorando pra voltar

`fetch()` nativo do Node não tem timeout nenhum por padrão. `api_client.py`
sempre teve (`timeout: float = 10.0` em toda chamada); o lado Node não
tinha equivalente até o usuário reportar que, depois de gravar, a volta
pra "Reuniões" "demorou um tempo chato". Se algo aceita a conexão na
porta da API mas nunca responde (outro serviço escutando ali por engano
-- já aconteceu de verdade nesta máquina, docs/15-roadmap.md Fase 7), o
`fetch()` trava indefinidamente em vez de falhar rápido com mensagem
clara (RNF-U02). Corrigido com `AbortSignal.timeout(10_000)`, mesmo valor
do Python, mais uma mensagem específica pra esse caso ("Tempo esgotado
conectando à API"). Testado isolado contra um servidor que aceita conexão
e nunca responde: erro em ~2s com timeout de 2s, `TimeoutError` detectado
certo.

## Mensagem de `rec` "por fora" -- pausa antes de limpar, não captura de stdout

`cronista rec` termina imprimindo algo que importa ("Áudio salvo, mas a
API não confirmou... fica pendente") direto no terminal, fora de
qualquer coisa que o Ink controle -- e o usuário reportou que essa
mensagem ficava "por fora", sem separação clara da tela do `cronista-tui`
que reaparece logo em seguida.

**Não dá pra simplesmente capturar essa saída** (`stdio: "pipe"` em vez
de `"inherit"` em `pythonBridge.js`): `rec` precisa do terminal de
verdade pra própria barra de sinal ao vivo (Rich `Live`), que também usa
stdout -- capturar quebraria a UI ao vivo da gravação, o problema
original que motivaria uma correção maior que o pedido.

Depois que `cronista rec` termina, `index.js` pausa esperando uma
confirmação antes de limpar e voltar pro Ink. A mensagem fica parada até
o usuário confirmar de propósito, em vez de piscar e ser atropelada pelo
redesenho seguinte -- não é a mensagem "dentro" de um `Notice.js`
estilizado (isso exigiria capturar/estruturar a saída do Python, fora de
escopo por ora), mas resolve a falta de separação.

**Quatro versões até acertar -- as três primeiras quebravam o processo
inteiro, sem erro visível (ou quase), ao voltar pro Ink.** Registrado
porque o padrão do erro (mesmo sintoma, causas diferentes cada vez) é o
achado real:

1. **v1**: `process.stdin.setRawMode()`/`.resume()`/`.pause()` mexido à
   mão em `index.js`, fora de qualquer componente Ink. Suspeita: modo raw
   ligado/desligado manualmente ficava dessincronizado do que o
   `render()` seguinte esperava encontrar no stdin.
2. **v2**: trocou a pausa por uma tela Ink de verdade (`PressKey.js`,
   `useApp`/`useInput`) -- eliminou a suspeita do item 1 (Ink também
   gerenciava a pausa, não só a tela principal), mas o usuário testou de
   novo e **quebrou do mesmo jeito**. A causa nunca foi "quem liga o modo
   raw" -- era chamar `render()` do Ink **uma segunda vez no mesmo
   processo**, não importa como a primeira pausa era feita.
3. **v3**: pausa com `node:readline` (`rl.question`, sem modo raw nenhum,
   sem `render()` nenhum) -- ainda Node puro controlando o stdin. O
   usuário testou de novo e **quebrou de novo**, desta vez com um aviso
   visível do próprio Node ("Detected unsettled top-level await",
   apontando pro `await` da pausa): o processo decidia que não tinha mais
   nada segurando o event loop e saía sozinho, com a Promise da pausa
   ainda pendente.
4. **v4 (atual)**: parar de fazer o Node gerenciar o teclado ele mesmo --
   delega pro `pause` nativo do Windows via processo filho
   (`spawnSync("cmd.exe", ["/c", "pause"], {stdio: "inherit"})`), o mesmo
   mecanismo `spawnSync`+`inherit` que `cronista rec`/`sync`/`login` já
   usam sem problema a sessão inteira. Bônus: `pause` já mostra a
   mensagem nativa em português do Windows ("Pressione qualquer tecla
   para continuar"), não precisa escrever a nossa.

A tela seguinte ("Reuniões") continua rodando num **processo Node novo**
(`spawnSync(process.execPath, [__filename], ...)`, `index.js` chamando a
si mesmo) -- nunca mais que um `render()` por processo, essa parte do
diagnóstico (item 2) segue valendo. `PressKey.js`, `node:readline` e o
`try/catch` em volta de um loop que não existe mais foram todos apagados
-- `index.js` é hoje uma sequência linear (monta, pausa se precisar,
spawna o próximo processo), não um loop.

Achado no caminho: `Sidebar`/`Meetings`/`Devices` tinham `useInput` sem
checar `stdout.isTTY` (só `focused`) -- corrigido gatingando tudo a
partir de um único `interactive = Boolean(stdout.isTTY)` em `App.js`.

**Não verificado ainda**: o ciclo completo, com o usuário escolhendo
"Gravar" de dentro de um terminal interativo de verdade, com esta v4 --
`cmd.exe /c pause` foi testado isolado (mostra a mensagem certa, sai
limpo), mas não dentro do fluxo Ink→Python→pause→Ink de ponta a ponta.

## Latência de ~3-5s escolhendo um lançador -- corrigido, era import de verdade

Medido, não presumido: `python -c "from cronista.client import cli"` sozinho
levava **~3s** (a maior fatia era `pydantic_settings`, ~1,7s -- via
`cronista.core.config.ClientSettings`),
mais **~1,7s** de `soundcard` enumerando dispositivo quando o comando é
`rec`. Antes da migração pra Ink, isso só acontecia **uma vez**, quando
`cronista` abria (o processo Python já ficava de pé; escolher "rec" no
`home.py` antigo era só uma chamada de função dentro do mesmo processo,
zero import novo). Agora, cada vez que um item "launch" é escolhido,
`pythonBridge.js` spawna um **processo Python do zero**, que paga esse
custo de importação de novo, sempre.

**Corrigido** (o usuário reclamou da demora duas vezes -- valia a pena
medir e resolver, não só documentar como trade-off aceito). Causa raiz:
`ClientSettings` (pydantic, em `cronista/core/config.py`) só precisa de
duas strings (`api_base_url`, `data_root`), mas `pydantic_settings`
sozinho -- a biblioteca, não o uso que a classe fazia dela -- já custava
~1,7s de import. Isso não tinha problema quando o processo Python ficava
de pé o programa inteiro; virou problema com processo novo por
lançador (ADR-0017).

`cronista/client/settings.py`: `ClientSettings` reescrito sem
`pydantic_settings` -- mesmos dois campos, mesmo `.env`, mesma
precedência (variável de ambiente real vence o arquivo; obrigatório sem
nenhum dos dois é erro claro), só que com um parser de `.env` de ~15
linhas em vez da lib inteira. `RECORDINGS_DIRNAME` também saiu de
`cronista/core/config.py` pra `cronista/core/paths.py` (sem
`pydantic_settings` no topo do arquivo) -- importar essa constante
sozinha já disparava o import da lib inteira, já que Python executa o
módulo inteiro na primeira importação, não só o nome pedido.
`cronista.core.config.ClientSettings` (pydantic) foi apagado -- ficou
sem consumidor depois da troca; `DatabaseSettings`/`WorkerSettings`/
`Settings` continuam como estavam, API e worker são processos de vida
longa onde esse custo é pago uma vez e não importa.

**Medido, não só trocado às cegas**: `python -c "from cronista.client
import cli"` caiu de ~3,1s pra ~0,77s (~4x), repetido duas vezes pra
confirmar. 259 testes Python passam (255 de antes + 4 novos, cobrindo o
parser de `.env`: variável de ambiente, arquivo, precedência entre os
dois, comentário/linha em branco ignorados, e erro claro quando falta
nos dois lugares).

## O que ainda não existe (registrado, não escondido)

- **Testado contra API real respondendo de verdade** (não só fora do
  ar): `listMeetings`/`getMeeting`+`getTranscript`/`search` confirmados
  contra dado real desta máquina, incluindo renovação silenciosa de
  token expirado (401 → `/auth/refresh` → salva o novo, sem pedir login
  de novo).
- Resumo sem estilo markdown (parágrafo acima).
- Centralização da Home só testada contra a largura fixa que
  `ink-testing-library` reporta (100 colunas, hardcoded na própria lib —
  não dá pra simular outra largura por ela). Redimensionar o terminal de
  verdade com `npm start` de pé é o único jeito real de conferir em
  outras larguras.
