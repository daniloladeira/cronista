# Identidade Visual e Animação do CLI

> **Versão:** 1.0 · **Última atualização:** 2026-08-17
> Decisão de biblioteca: [ADR-0015](adr/0015-rich-como-apresentacao-cli.md).
> **Este documento não introduz requisito novo.** Especifica como RF-05, RNF-U01, RNF-U02 e RNF-U03 se manifestam na tela. Se algum dia divergir de [11-cli.md](11-cli.md), aquele documento é quem define comportamento; este define aparência.

## 1. Motivação e referência

Ponto de partida: o artigo da engenharia por trás do banner animado do [GitHub Copilot CLI](https://github.blog/engineering/from-pixels-to-characters-the-engineering-behind-github-copilot-clis-animated-ascii-banner/). A implementação ali é TypeScript sobre Ink; não se aplica diretamente a um projeto Python com Typer, mas várias das decisões de design se sustentam independente da linguagem.

**O que foi adotado do artigo:**

- Cor por **papel semântico** (`voce`, `outros`, `sucesso`, `erro`, `atenção`), não código de cor fixo — o papel se traduz em cor no momento de desenhar, permitindo tema claro e escuro
- Animação como melhoria **não bloqueante**: nunca atrasa o comando de fazer o que precisa fazer
- Desligamento automático quando a saída não é um terminal interativo (redirecionamento, pipe, CI) ou quando o usuário pediu explicitamente para não ter animação
- Ritmo de quadro em torno de 75ms (~13fps) — rápido o bastante para parecer vivo, devagar o bastante para não piscar

**O que não se aplica e foi descartado:** editor de frames dedicado (o artigo construiu um; aqui a escala do projeto não paga esse investimento — ver §7), framework de componentes tipo Ink (não existe equivalente direto em Python; Rich cobre o necessário sem esse nível de aparato).

**O que foi decidido diferente, deliberadamente:** o artigo evitou gradiente de cor por causa da fragmentação de terminal. Aqui o gradiente entrou mesmo assim, por pedido explícito do usuário, aceitando o risco de degradar mal em terminal sem truecolor — mitigado pela detecção automática do Rich (§5).

## 2. Princípios

| Princípio | O que significa na prática |
|---|---|
| Decoração, não mudança de modelo | Todo comando continua sendo uma função que roda e termina (ADR-0015) |
| Nunca bloqueia | Uma animação de abertura não atrasa o comando real; um spinner de rede desaparece assim que a resposta chega |
| Desliga sozinho quando precisa | Saída redirecionada, `NO_COLOR` definido, ou terminal sem suporte a cor: sem animação, sem código ANSI vazando pro arquivo |
| Papel semântico, não cor fixa | Cada elemento tem um papel (`voce`, `outros`, `sucesso`, `erro`, `atenção`, `neutro`); a paleta traduz papel em cor, não o código |
| Onde há espera real, ou onde a spec já pedia sinal visual | Anima porque há algo acontecendo que vale mostrar, não decoração por decoração |

## 3. Onde aparece

| Momento | Elemento visual | Vínculo com a spec |
|---|---|---|
| `cronista` sem comando, primeira execução do dia | Banner de abertura curto (poucos segundos) | Estético; segue a restrição do artigo de não aparecer a cada invocação |
| Qualquer chamada de rede (`login`, `refresh`, envio de trilha, busca) | Indicador de status (`rich.status`) enquanto espera a resposta | RNF-U01, RNF-U03 — o usuário sabe que algo está acontecendo, e se foi rápido ou travou |
| `cronista rec`, durante a gravação | **Barra de gradiente como medidor de sinal**, uma por trilha (`voce`, `outros`) | É a implementação visual de **RF-05**, que já exigia indicação de sinal por trilha |
| Transcrição (Fase 3) | Barra de progresso | Ainda não implementado; registrado aqui para não ser esquecido quando a Fase 3 chegar |
| Erro | Texto no papel `erro`, sem animação | RNF-U02 — mensagem de erro não é hora de efeito visual, é hora de clareza |

**A barra de gradiente do `rec` é o elemento mais importante desta lista.** Não é decoração: é a resposta visual ao requisito que já existia. Um medidor que sobe e desce com o volume captado é o que permite notar, durante a reunião, que um microfone está mudo — que é exatamente o cenário que RF-05 foi escrito para prevenir.

## 4. Paleta por papel semântico

| Papel | Uso | Tema claro | Tema escuro |
|---|---|---|---|
| `voce` | Trilha do microfone, elementos "seus" | verde escuro | verde claro |
| `outros` | Trilha de loopback, elementos "dos outros" | azul escuro | azul claro |
| `sucesso` | Confirmação, término correto | verde | verde |
| `erro` | Falha, RNF-U02 | vermelho | vermelho |
| `atencao` | Advertência não bloqueante (ex.: trilha sem sinal) | amarelo/laranja | amarelo |
| `neutro` | Texto comum | cor padrão do terminal | cor padrão do terminal |

Valores de RGB exatos ficam para a implementação, não para este documento — travar hexadecimal aqui seria decisão prematura antes de ver o resultado no terminal real.

## 5. Mecânica técnica

Primitivas do Rich usadas, e por que cada uma:

| Necessidade | Primitiva do Rich |
|---|---|
| Região que se redesenha sem piscar | `rich.live.Live` — resolve o mesmo problema que o artigo resolveu com `readline.cursorTo()` + `clearScreenDown()` |
| Indicador de espera em chamada de rede | `rich.status.Status` |
| Barra de progresso | `rich.progress.Progress` |
| Texto colorido por papel semântico | `rich.style.Style`, mapeado por tabela de papéis (§4) |
| Barra de gradiente (RF-05) | Renderização própria sobre `rich.console.Console`, um caractere por vez com cor RGB interpolada — mesma lógica do protótipo em `scripts/preview_gradient_bar.py` |

**Detecção de capacidade — a parte que o Rich resolve de graça.** O artigo do GitHub implementou detecção de tema e modo leitor de tela à mão. O `Console` do Rich detecta sozinho:

- `color_system`: `truecolor`, `256`, `standard` (16 cores) ou `None` — a barra de gradiente degrada de suave para blocos de cor para sem cor, automaticamente
- `NO_COLOR` no ambiente — desliga cor por completo, respeitando o padrão que a comunidade de terminal já usa
- `console.is_terminal` — falso quando a saída é redirecionada; a animação nem tenta rodar

Isso é o que torna razoável usar gradiente aqui, mesmo o artigo do GitHub tendo evitado: o risco de quebrar em terminal antigo existe, mas a biblioteca já trata a queda de qualidade sozinha, em vez de exigir código próprio para cada caso.

## 6. Barra de gradiente: como funciona

A técnica, testada e aprovada pelo usuário em `scripts/preview_gradient_bar.py` antes de entrar na spec:

1. A barra é uma sequência de caracteres de bloco (`▁▂▃▄▅▆▇█`)
2. Cada posição na largura da barra tem uma cor interpolada entre dois papéis semânticos (ex.: `sucesso` → `atencao` → `erro`, para um medidor de volume)
3. O nível atual (0 a 1) determina quantos caracteres aparecem preenchidos
4. Redesenha na mesma região, sem imprimir linha nova, no ritmo de ~75ms (§1)

**Não há arte pré-desenhada aqui.** Ao contrário do banner (§7), a barra é calculada em tempo real a partir de um valor (nível de áudio, percentual de progresso) — não existe "quadro" para autorar, só a função que traduz valor em caracteres e cor.

## 7. Formato dos ativos do banner

O banner de abertura, ao contrário da barra, é arte de verdade — alguém desenha.

**Decisão deliberada: sem editor de frames dedicado.** O artigo do GitHub construiu um (`ascii-motion.app`) porque a escala do projeto deles justificava. Aqui, os quadros do banner são arquivos de texto simples em `cronista/client/art/`, um por quadro (`banner_01.txt`, `banner_02.txt`, ...), com as posições de cor mapeadas à parte, em código, por papel semântico — mesma separação de conteúdo e cor que o artigo descreve, só que sem ferramenta própria para produzi-la.

## 8. Plano de teste das artes

O que foi pedido explicitamente: testar antes de integrar.

**Já testado.** `scripts/preview_gradient_bar.py` — protótipo descartável, sem dependência do projeto, que reproduziu a técnica de gradiente truecolor no terminal real do usuário. Aprovado. Vira a referência de comportamento para a implementação real dentro de `cronista/client/`, e será removido quando ela existir.

**A testar quando o banner existir.** `scripts/preview_banner.py`, no mesmo espírito: reproduz os quadros do banner isoladamente, sem precisar rodar o CLI inteiro, para iterar no desenho rápido.

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
| Aplicativo de terminal persistente (Textual) | Decisão explícita do ADR-0015, com gatilho de reversão próprio |

## 10. Documentos relacionados

| Documento | Papel |
|---|---|
| [ADR-0015](adr/0015-rich-como-apresentacao-cli.md) | Por que Rich, e não Textual |
| [ADR-0006](adr/0006-cli-antes-de-desktop.md) | A tensão que motivou a escolha |
| [11-cli.md](11-cli.md) | Comportamento dos comandos; este documento trata só de aparência |
| [03-requisitos.md](03-requisitos.md) | RF-05, RNF-U01 a RNF-U03 — os requisitos que este documento implementa visualmente |
