# ADR-0015 · Rich como biblioteca de apresentação do CLI

- **Status:** aceito
- **Data:** 2026-08-17
- **Requisitos relacionados:** RF-05, RNF-U01, RNF-U02, RNF-U03 (nenhum requisito novo, ver [17-identidade-visual-cli.md](../17-identidade-visual-cli.md))

## Contexto

O usuário pediu um CLI "cheio de animações e com bom design", citando o artigo da engenharia do banner animado do GitHub Copilot CLI como referência. A implementação descrita ali é TypeScript sobre Ink (React para terminal), incompatível com um projeto Python baseado em Typer.

Existiam dois caminhos reais de adaptação, com consequência de arquitetura diferente:

1. **Decorar o modelo atual** — cada comando continua sendo uma função que roda e termina; a apresentação ganha cor, spinner, barra de progresso e barra de gradiente por cima.
2. **Trocar o modelo de interação** — um aplicativo de terminal persistente (Textual), com loop de eventos e navegação, mais parecido com `htop` que com um comando pontual.

O [ADR-0006](0006-cli-antes-de-desktop.md) já havia decidido CLI antes de desktop com uma razão explícita: depurar captura de áudio dentro de loop de evento gráfico multiplica a dificuldade. Um aplicativo Textual é da mesma categoria de complexidade que aquele ADR evitou, e a gravação (`cronista rec`) é justamente a única operação irreversível do sistema. Colocar essa opção sobre a mesa, com o trade-off explícito, coube ao usuário — que escolheu decorar o modelo atual.

## Decisão

Usar **Rich** como camada de apresentação em todo o CLI. Nenhum comando muda de modelo: cada um continua sendo uma função que roda e termina. Rich decora com banner de abertura, indicador de status durante chamadas de rede, barra de gradiente como medidor de sinal (RF-05) e barra de progresso em operações longas.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Textual (app de terminal persistente) | Reintroduziria a complexidade de loop de evento que o ADR-0006 evitou, justo no comando de maior risco do sistema |
| ANSI puro, sem biblioteca | Reimplementaria à mão detecção de capacidade de terminal, degradação de cor e respeito a `NO_COLOR` — problemas que o artigo do GitHub resolveu construindo ferramenta própria, e que o Rich já resolve testado |
| Equivalente a Ink em Python | Não existe directo; o ecossistema Python de terminal gira em torno de Rich/Textual |

## Consequências

**Positivas.** O `Console` do Rich detecta sozinho o `color_system` do terminal (truecolor, 256 cores, 16 cores, ou nenhuma) e degrada automaticamente — é o mesmo problema que o artigo do GitHub resolveu escrevendo ferramenta própria, aqui resolvido pela biblioteca. Rich respeita `NO_COLOR` nativamente e detecta saída não-interativa (desliga animação sozinho quando a saída é redirecionada para arquivo ou pipe). Ecossistema já próximo do Typer.

**Negativas.** Dependência nova declarada explicitamente. Gradiente de verdade exige suporte a truecolor, que nem todo terminal Windows oferece — `cmd.exe` clássico não tem; Windows Terminal moderno tem. O próprio artigo do GitHub evitou gradiente por essa razão exata, preferindo 16 cores fixas por compatibilidade máxima. Aqui o risco foi aceito conscientemente, com a degradação automática do Rich como rede de segurança quando o terminal não suporta.

## Gatilho de reversão

Se o modelo "comando roda e termina" se mostrar insuficiente para o que o usuário efetivamente quer no uso diário, por exemplo desejar navegação persistente ou um painel ao vivo, Textual volta à mesa. Nesse caso a decisão deste ADR precisa ser revisitada junto do ADR-0006, já que os dois tratam do mesmo tipo de risco.
