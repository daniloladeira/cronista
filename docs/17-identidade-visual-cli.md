# Identidade Visual e Animação do CLI

> **Versão:** 1.5 · **Última atualização:** 2026-08-18
> Decisões de biblioteca: [ADR-0015](adr/0015-rich-como-apresentacao-cli.md) (Rich, comandos que rodam e terminam), [ADR-0016](adr/0016-textual-para-navegacao.md) (Textual, painel navegável de `list`/`ler`/`buscar`).
> Este documento trata da parte em Rich — banner, indicador de sinal, spinners. O painel Textual ganha especificação visual própria quando a Fase 5 chegar.
> **Este documento não introduz requisito novo.** Especifica como RF-05, RNF-U01, RNF-U02 e RNF-U03 se manifestam na tela. Se algum dia divergir de [11-cli.md](11-cli.md), aquele documento é quem define comportamento; este define aparência.

## 1. Motivação e referência

Ponto de partida: o artigo da engenharia por trás do banner animado do [GitHub Copilot CLI](https://github.blog/engineering/from-pixels-to-characters-the-engineering-behind-github-copilot-clis-animated-ascii-banner/). A implementação ali é TypeScript sobre Ink; não se aplica diretamente a um projeto Python com Typer, mas várias das decisões de design se sustentam independente da linguagem.

**O que foi adotado do artigo:**

- Cor por **papel semântico** (`voce`, `outros`, `sucesso`, `erro`, `atenção`), não código de cor fixo — o papel se traduz em cor no momento de desenhar, permitindo tema claro e escuro
- Animação como melhoria **não bloqueante**: nunca atrasa o comando de fazer o que precisa fazer
- Desligamento automático quando a saída não é um terminal interativo (redirecionamento, pipe, CI) ou quando o usuário pediu explicitamente para não ter animação
- Ritmo de quadro em torno de 75ms (~13fps) — rápido o bastante para parecer vivo, devagar o bastante para não piscar

**O que não se aplica e foi descartado:** editor de frames dedicado (o artigo construiu um; aqui a escala do projeto não paga esse investimento — ver §7), framework de componentes tipo Ink (não existe equivalente direto em Python; Rich cobre o necessário sem esse nível de aparato).

**O que foi decidido diferente, e depois revertido de volta.** A primeira versão do medidor de sinal usava gradiente de cor contínuo (verde→amarelo→vermelho), justamente o que o artigo evitou por causa da fragmentação de terminal. Testado de verdade no terminal do usuário, o gradiente foi **rejeitado por gosto**, não por limitação técnica: "não tá pixelizado". A versão final usa blocos sólidos em estados discretos ligado/desligado — mais parecido com o artigo do GitHub (que também usa blocos, não gradiente) do que a primeira tentativa. Ver §6.

## 2. Princípios

| Princípio | O que significa na prática |
|---|---|
| Decoração, não mudança de modelo | Todo comando continua sendo uma função que roda e termina (ADR-0015) |
| Nunca bloqueia | Uma animação de abertura não atrasa o comando real; um spinner de rede desaparece assim que a resposta chega |
| Desliga sozinho quando precisa | Saída redirecionada, `NO_COLOR` definido, ou terminal sem suporte a cor: sem animação, sem código ANSI vazando pro arquivo |
| Uma cor principal, o resto neutro | Dourado (`#DFB878`) é a cor de identidade do sistema; tudo que não precisa competir por atenção fica neutro (§4) |
| Onde há espera real, ou onde a spec já pedia sinal visual | Anima porque há algo acontecendo que vale mostrar, não decoração por decoração |

## 3. Onde aparece

| Momento | Elemento visual | Vínculo com a spec |
|---|---|---|
| `cronista` sem comando, primeira execução do dia | Banner de abertura curto (poucos segundos) | Estético; segue a restrição do artigo de não aparecer a cada invocação |
| Qualquer chamada de rede (`login`, `refresh`, envio de trilha, busca) | Indicador de status (`rich.status`) enquanto espera a resposta | RNF-U01, RNF-U03 — o usuário sabe que algo está acontecendo, e se foi rápido ou travou |
| `cronista rec`, durante a gravação | Tela em tela cheia (`Live(..., screen=True)`): régua "cronista" no topo, cabeçalho numa linha só (título à esquerda, **traço fino por trilha embutido à direita** — `voce`/`outros`, ver `signal_bar.py` `render_header_trace()`), rodapé com duração. **Sem barra grande separada** — o traço do cabeçalho é o único indicador, layout decidido em `scripts/preview_rec_screen.py` | É a implementação visual de **RF-05**, que já exigia indicação de sinal por trilha |
| `cronista rec`, durante uma pausa (RF-31) | O traço de sinal, à direita do cabeçalho, vira o texto "pausado" (âmbar, sem emoji); a duração no rodapé para de contar (RN-11: tempo pausado não é gravação). Decidido com preview visual comparado com o usuário antes de implementar, não só descrito em texto | RF-31 |
| `cronista rec`, título da aba/janela do terminal | `"gravando · <título>"` / `"pausado · <título>"`, sequência OSC + `SetConsoleTitleW` no Windows (`signal_bar.py` `_set_tab_title()`, inspirado em `TabTitle.tsx` do projeto torlink) | Acha a janela certa numa reunião longa sem precisar voltar pro terminal — mesmo espírito de RF-05 |
| Transcrição (Fase 3) | Barra de progresso | Ainda não implementado; matemática do brilho já portada (`cronista/client/sheen.py`), sem consumidor — registrado aqui para não ser esquecido |
| Erro | Texto no papel `erro`, sem animação | RNF-U02 — mensagem de erro não é hora de efeito visual, é hora de clareza |

**O indicador de sinal do `rec` é o elemento mais importante desta lista.** Não é decoração: é a resposta visual ao requisito que já existia. Um traço que sobe e desce com o volume captado é o que permite notar, durante a reunião, que um microfone está mudo — que é exatamente o cenário que RF-05 foi escrito para prevenir.

## 4. Paleta

Mais simples do que a primeira versão deste documento previa. Em vez de seis papéis semânticos com cor própria, o sistema tem **uma cor de identidade**, um neutro, e um terceiro papel que só aparece num estado específico:

| Papel | Cor | Uso |
|---|---|---|
| **Principal** | `#DFB878` (dourado) | Cor de identidade do Cronista. Trilha `voce` no medidor de sinal; reservado para banner, títulos e destaques quando existirem |
| **Neutro** | `#A6A6A6` (cinza, sem calor nenhum) | Trilha `outros`, e qualquer elemento que não deva competir com a cor principal |
| **Apagado** | `#2A2A2A` | Estado "sem sinal" do medidor de LED — nunca preto puro, pra continuar visível como parte da escada |
| **Pausado** | `#BA7517` (âmbar) | Único uso: `cronista rec` durante uma pausa (RF-31, §3). Não é um papel geral de "atenção" — é específico desse estado, pra não repetir o problema que a v1 deste documento teve com seis cores pouco usadas |

**`erro`, `sucesso` e `atenção` ficam deliberadamente em aberto.** A primeira versão deste documento inventou uma paleta narrativa de seis cores (tema "manuscrito iluminado") sem o usuário ter pedido — corrigido depois que ele apontou que só havia dado uma cor, o dourado, como identidade principal. Fica registrado o erro para não repetir: **não inventar papel de cor que não foi pedido.** Esses três papéis são decididos quando o CLI realmente precisar deles (mensagem de erro, confirmação de sucesso), não antes.

## 5. Mecânica técnica

Primitivas do Rich usadas, e por que cada uma:

| Necessidade | Primitiva do Rich |
|---|---|
| Região que se redesenha sem piscar | `rich.live.Live` — resolve o mesmo problema que o artigo resolveu com `readline.cursorTo()` + `clearScreenDown()` |
| Indicador de espera em chamada de rede | `rich.status.Status` |
| Barra de progresso | `rich.progress.Progress` |
| Texto na cor de identidade ou neutro | `rich.style.Style`, com os dois tons de §4 |
| Medidor de LED (RF-05) | `rich.text.Text` com um estilo por linha (bloco cheio `██`), ligado ou apagado — `cronista/client/signal_bar.py` |

**Detecção de capacidade — a parte que o Rich resolve de graça.** O artigo do GitHub implementou detecção de tema e modo leitor de tela à mão. O `Console` do Rich detecta sozinho:

- `color_system`: `truecolor`, `256`, `standard` (16 cores) ou `None` — o dourado (`#DFB878`) e o cinza neutro se aproximam da cor mais próxima disponível automaticamente, sem código extra
- `NO_COLOR` no ambiente — desliga cor por completo, respeitando o padrão que a comunidade de terminal já usa
- `console.is_terminal` — falso quando a saída é redirecionada; a animação nem tenta rodar

Como o medidor de sinal final usa só duas cores fixas (§4), não estados discretos gerados por interpolação, a degradação automática do Rich importa menos aqui do que importaria para um gradiente — mas segue sendo o que protege qualquer cor futura (banner, quando existir) sem exigir tratamento manual por terminal.

## 6. Medidor de LED: como funciona

> **Superado.** A "versão final" abaixo (escada vertical de 10 células) foi consolidada no traço fino embutido no cabeçalho (§3) — não existe mais como bloco separado na tela. Fica registrado por ser o processo que levou até lá: as tentativas rejeitadas explicam por que o traço final é "pixelizado" e não um gradiente contínuo, mesmo em uma linha só.

Duas tentativas antes desta, ambas testadas de verdade no terminal e descartadas por não agradar, não por limitação técnica — vale registrar o processo, não só o resultado:

**Tentativa 1 — barra de gradiente contínuo.** Cor interpolada por posição ao longo de uma barra horizontal (`▁▂▃▄▅▆▇█`), do tipo verde→amarelo→vermelho. Rejeitada: "não tá pixelizado".

**Tentativa 2 — painel com borda pulsando.** Cada trilha num container com título, a cor da borda variando de apagada a viva conforme o volume, com um ponto central fazendo o mesmo. Rejeitada: "não faz nenhum sentido".

**Versão final — escada de LED vertical**, inspirada no [cava](https://github.com/karlstav/cava) (Console Audio Visualizer, um clássico do terminal Linux): blocos sólidos (`██`) em estados **discretos** ligado ou apagado, sem interpolação de brilho nem de posição.

1. Cada trilha é uma coluna de 10 células, de cima para baixo
2. O nível atual (0 a 1) determina quantas células, contando de baixo, ficam "acesas" — as demais ficam na cor apagada (§4)
3. `voce` acende na cor principal (dourado); `outros`, no neutro (cinza) — a mesma distinção de cor que diferencia as trilhas em qualquer lugar do sistema
4. Redesenha a cada atualização de nível, no ritmo de ~75ms (§1), via `rich.live.Live`

**Por que "pixelizado" importa aqui.** Estados discretos, sem gradiente nem interpolação suave, é o que dá a textura de equipamento de áudio retrô — e coincide, sem ter sido o objetivo original, com o próprio artigo do GitHub: eles também usam blocos, não gradiente contínuo. A primeira tentativa deste projeto tinha se afastado disso; a versão final voltou a convergir.

**Não há arte pré-desenhada aqui.** Ao contrário do banner (§7), o medidor é calculado em tempo real a partir de um valor (nível de áudio) — não existe "quadro" para autorar, só a função que traduz nível em células acesas.

## 7. Banner de abertura

> **Status: implementado** (`cronista/client/banner.py`). O plano original desta seção previa arte desenhada à mão, em quadros animados, com arquivos de texto em `cronista/client/art/` — descartado. O que existe é mais simples: fonte de bloco gerada (`pyfiglet`, fonte `ansi_shadow`) mais um degradê de cor, estático, sem animação.

**A cor não é degradê por letra nem contínuo simples.** É a técnica do projeto [torlink](https://github.com/baairon/torlink) (`src/ui/components/Logo.tsx`, `src/ui/theme.ts`), adaptada de roxo para os tons dourados de identidade do Cronista: cada **caractere** (não cada letra) recebe uma cor calculada por uma grade 2D — posição de linha e coluna combinadas — passando por quatro paradas de cor (`_HIGHLIGHT → _TOP → _ACCENT → _BASE → _SHADE`, ver `banner._sheen()`). O ponto mais escuro (`_SHADE = #B8934F`) nunca escurece além de um dourado reconhecível — duas tentativas anteriores foram rejeitadas por escurecerem demais.

**Tentativas rejeitadas, registradas pelo mesmo motivo do §6: vale saber o caminho, não só o resultado.** Um ícone de pergaminho sobre a letra "O" (primeiro em linha fina `╭─╮`, depois em bloco sólido `▄█▀`) foi testado duas vezes e rejeitado as duas — tirado de vez. Um degradê por letra simples (claro → escuro numa progressão linear) também foi tentado antes da técnica do torlink e achado insosso demais.

**Fallback por largura de terminal**, mesmo padrão do `Splash.tsx` do torlink (`showLogo = cols >= LOGO_WIDTH + 2`): banner grande só se couber; terminal estreito cai pro nome simples em cor de identidade; saída não-interativa (redirecionada) cai pro texto puro, sem código ANSI.

**Aparece só na primeira execução do dia** (`cronista` sem subcomando), com um marcador simples em `DATA_ROOT/.banner_shown` — mesmo espírito do artigo do GitHub Copilot CLI (§1) de não repetir a cada invocação. (Uma tentativa de virar menu navegável, ADR-0016, foi feita e revertida no mesmo dia — ver a nota lá.)

## 8. Plano de teste das artes

O que foi pedido explicitamente: testar antes de integrar.

**Já testado.** Quatro protótipos descartáveis, testados de verdade no terminal do usuário: gradiente contínuo, quatro variações de paleta (arco-íris, VU clássico, cor sólida, duas tonalidades), painel com borda pulsando, e a escada de LED final. Os três primeiros foram removidos do repositório depois da decisão — não há razão para manter código de uma direção descartada. `scripts/preview_led_meter.py` é o único que sobrevive, como referência de comportamento para `cronista/client/signal_bar.py`, e será removido quando o medidor estiver de fato integrado ao comando `rec` (Fase 2, etapa 5).

**Banner testado da mesma forma**, com scripts descartáveis iterados ao vivo com o usuário (`scripts/preview_banner_colors.py`, entre outras tentativas) até convergir na técnica do torlink (§7); removidos do repositório depois de integrados de verdade em `cronista/client/banner.py`, mesma prática do parágrafo acima.

**Critérios de aceitação, antes de qualquer elemento visual ser aceito como pronto:**

| Critério | Como verificar |
|---|---|
| Aparência em tema claro e escuro do Windows Terminal | Manual, nos dois temas |
| Saída redirecionada não emite código ANSI | `cronista list > arquivo.txt`, inspecionar o arquivo |
| `NO_COLOR=1` desliga cor sem quebrar o texto | Manual, com a variável definida |
| Terminal sem truecolor degrada sem lixo visual | Testar em `cmd.exe` clássico, não só Windows Terminal |
| Animação não atrasa o comando | Cronometrar `cronista rec` com e sem o indicador de sinal ligado |

## 9. Fora de escopo

| Fora de escopo | Por quê |
|---|---|
| Editor de frames dedicado | Não se paga na escala deste projeto (§7) |
| Animação em todo comando, sem critério | Contraria o princípio de "onde há espera real" (§2) |
| Aplicativo de terminal persistente **em `rec`** | O gatilho de reversão do ADR-0015 disparou, mas só para `list`/`ler`/`buscar` (ADR-0016). `rec` continua fora, de propósito — é a operação irreversível do sistema |

## 10. Documentos relacionados

| Documento | Papel |
|---|---|
| [ADR-0015](adr/0015-rich-como-apresentacao-cli.md) | Por que Rich para os comandos que rodam e terminam |
| [ADR-0016](adr/0016-textual-para-navegacao.md) | Por que Textual entrou depois, só para `list`/`ler`/`buscar` |
| [ADR-0006](adr/0006-cli-antes-de-desktop.md) | A tensão que motivou a escolha |
| [11-cli.md](11-cli.md) | Comportamento dos comandos; este documento trata só de aparência |
| [03-requisitos.md](03-requisitos.md) | RF-05, RNF-U01 a RNF-U03 — os requisitos que este documento implementa visualmente |
| [Referência Rich](referencia-rich.md) | Guia técnico de API — este documento explica o porquê, aquele explica o como |
