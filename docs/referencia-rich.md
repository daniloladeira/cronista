# Referência Rich

> Documento técnico, não spec do produto — por isso fora da sequência numerada `01-17`.
> Cobre só o que o Cronista usa de verdade, testado nesta sessão contra o Windows Terminal real. Não é a documentação completa do Rich — essa fica em [rich.readthedocs.io](https://rich.readthedocs.io/). Isto aqui é o atalho pra não redescobrir a mesma coisa duas vezes.

## 1. Gotchas encontrados nesta sessão

A parte mais importante do documento — problemas reais que custaram uma rodada de correção cada.

| Sintoma | Causa | Solução |
|---|---|---|
| Recuo esquerdo inconsistente entre elementos | Prefixo manual `"  "` em cada `Text`, um esquecido em algum lugar | Um `Padding` só, em volta do `Group` inteiro (§6) |
| Régua com título aparece no meio, não à esquerda | `Rule` centraliza o título por padrão | `Rule(title, align="left")` |
| Tela pisca com conteúdo grande (painel, grade multi-linha) | `Live` em modo inline (`screen=False`, o padrão) redesenha por reposicionamento de cursor; blocos grandes ficam visíveis piscando | `Live(..., screen=True)` — usa buffer de tela alternativo, mesmo mecanismo do vim/htop |
| Duas trilhas atualizando ao mesmo tempo bagunçam a tela | Duas threads chamando `print`/`Live.update` sem coordenação | Um `threading.Lock()` em volta de toda leitura+escrita do estado compartilhado; só uma chamada de `Live.update()` por vez |
| Barra de nível mal responde a fala normal | Nível de áudio é linear, percepção de volume não é | Curva de resposta: `nivel ** 0.3` antes de mapear pra altura/cor (aproxima log/percepção) |

## 2. `Console`

```python
from rich.console import Console
console = Console()
```

- `console.color_system` — detecta sozinho: `"truecolor"`, `"256"`, `"standard"` (16 cores) ou `None`. Cor hexadecimal (`"#DFB878"`) degrada pra aproximação automaticamente; não precisa checar isso na mão.
- Respeita `NO_COLOR` no ambiente nativamente.
- `console.is_terminal` — `False` quando a saída é redirecionada (`> arquivo.txt` ou pipe). Não precisa checar `sys.stdout.isatty()` você mesmo.

## 3. `Live` — a região que se redesenha

```python
from rich.live import Live

with Live(console=console, refresh_per_second=13, screen=True) as live:
    live.update(algum_renderable)
```

| Parâmetro | Efeito |
|---|---|
| `screen=True` | Buffer de tela alternativo — limpa tudo ao entrar, restaura o terminal exato de antes ao sair. Zero rastro no histórico de rolagem. Use pra telas que ficam abertas (ex.: `cronista rec`) |
| `screen=False` (padrão) | Redesenho inline, no lugar onde o comando foi chamado. Fica rastro no scroll. Pisca mais com conteúdo grande |
| `refresh_per_second=13` | Ritmo usado em todo o projeto — ~75ms por quadro, referência do artigo do GitHub Copilot CLI (docs/17 §1) |

**Não é thread-safe sozinho.** Se mais de uma thread chama `.update()`, envolva com `threading.Lock()` (ver `cronista/client/signal_bar.py`).

**Uso fora de `with`:** `live.__enter__()` / `live.__exit__(*exc_info)` diretamente, quando o ciclo de vida não bate com um único bloco `with` (ex.: `SignalBar` como classe reutilizável).

## 4. `Text` — string com estilo

```python
from rich.text import Text

t = Text("prefixo ")            # texto inicial, sem estilo
t.append("colorido", style="#DFB878")   # hex direto funciona como style
t.append("negrito", style="bold #DFB878")
```

- `\n` dentro de uma string cria múltiplas linhas dentro do MESMO `Text`.
- Concatenar estilos: `f"bold {VOCE_COLOR}"` funciona como string de estilo.

## 5. `Group` — empilhar verticalmente

```python
from rich.console import Group
Group(elemento1, elemento2, elemento3)  # cada um em sua própria linha/bloco
```

Não adiciona espaço entre os elementos sozinho — para respiro, inclua `Text("")` como elemento entre eles.

## 6. `Padding` — recuo num lugar só

```python
from rich.padding import Padding
Padding(conteudo, (vertical, horizontal))  # ex.: (0, 2) = 2 colunas de cada lado, sem recuo vertical
```

**Use isto em vez de prefixar `"  "` manualmente em cada `Text`.** Foi a causa raiz de três desalinhamentos consecutivos nesta sessão — cada elemento reinventava o próprio recuo até um ficar diferente do outro.

## 7. `Table.grid` — colunas, sem borda

```python
from rich.table import Table

grid = Table.grid(expand=True)     # expand=True: ocupa a largura do terminal
grid.add_column(justify="left")
grid.add_column(justify="right")
grid.add_row(conteudo_esquerda, conteudo_direita)
```

Uso no projeto: cabeçalho do `cronista rec` — título à esquerda, indicador de sinal à direita, mesma linha, alinhado automaticamente à largura real do terminal (`docs/11-cli.md`, layout do cabeçalho).

## 8. `Panel` — caixa com borda

```python
from rich import box
from rich.panel import Panel

Panel(conteudo, title="voce", border_style="#DFB878", box=box.ROUNDED)
```

`box.ROUNDED` dá cantos arredondados com caracteres Unicode (`╭╮╰╯`) — é o que se aproxima de "canto suave" no terminal, sem ser de verdade renderização de pixel.

*(Testado nesta sessão, depois descartado do layout final do `rec` — o usuário preferiu o cabeçalho embutido sem painel. Fica registrado porque pode servir em outra tela.)*

## 9. `Rule` — linha divisória

```python
from rich.rule import Rule
Rule(Text("cronista", style="bold #DFB878"), style="#DFB878", align="left")
```

**`align` tem que ser explícito.** O padrão é `"center"` — pegou a gente de surpresa, o título apareceu no meio da linha em vez de perto da margem esquerda.

## 10. `Columns` — lado a lado, com quebra

```python
from rich.columns import Columns
Columns([elemento1, elemento2], padding=(0, 4))
```

Diferente de `Table.grid`: não tem noção de "coluna que ocupa a largura toda" — apenas coloca os elementos lado a lado e quebra linha se não couber. Usado nos protótipos de comparação (`voce` e `outros` lado a lado).

## 11. Cor: tom vs. matiz

Técnica usada em `signal_bar.py` pra gradiente sem introduzir cor nova:

```python
def _tone(base_hex: str, intensity: float) -> str:
    r = int(base_hex[1:3], 16)
    g = int(base_hex[3:5], 16)
    b = int(base_hex[5:7], 16)
    frac = MIN_TONE + (1 - MIN_TONE) * max(0.0, min(intensity, 1.0))
    return f"#{int(r*frac):02x}{int(g*frac):02x}{int(b*frac):02x}"
```

Escala a MESMA cor entre um piso (`MIN_TONE`, nunca preto puro) e o valor cheio — dá profundidade sem virar arco-íris. Rejeitado no projeto: gradiente de matiz (`verde→amarelo→vermelho`) — ver `docs/17-identidade-visual-cli.md` §1 e §6 pro histórico completo da decisão.

## 12. Não coberto aqui

Textual (framework separado, mesma equipe do Rich) tem API própria — não documentado neste arquivo. Entra quando a Fase 5 (ADR-0016) começar a ser implementada, como referência própria.

## 13. Onde isso é usado no projeto

| Arquivo | O que faz |
|---|---|
| `cronista/client/signal_bar.py` | `Live`, `Text`, `Group`, tom de cor (§11) |
| `scripts/preview_rec_screen.py` | `Padding`, `Rule`, `Table.grid`, composição completa |
| `docs/17-identidade-visual-cli.md` | Decisões de design que motivaram cada escolha técnica daqui |
