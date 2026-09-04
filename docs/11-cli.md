# Linha de Comando · Contrato

> **Versão:** 1.6 · **Última atualização:** 2026-09-04
> Decisões correspondentes: [0006](adr/0006-cli-antes-de-desktop.md), [0015](adr/0015-rich-como-apresentacao-cli.md), [0016](adr/0016-textual-para-navegacao.md)

## 1. Papel

A linha de comando é a primeira interface, e serve de contrato para a interface desktop que virá depois (Fase 8). Tudo que ela faz, faz chamando a API, exceto capturar áudio e listar dispositivos, que são locais por natureza.

O executável chama-se `cronista` ([16-nome.md](16-nome.md)).

**O CLI tem dois modelos de interação, não um só (ADR-0016).** A maioria dos comandos roda e termina — decorados com Rich (ADR-0015). `list`, `ler` e `buscar` convergem numa experiência navegável e persistente com Textual, porque o usuário pediu explicitamente poder navegar pelo acervo, ler transcrição trocando de aba e percorrer busca sem comando novo a cada passo. `rec` **fica de fora dessa navegação** de propósito — é a única operação irreversível do sistema (ADR-0012), e misturar isso com loop de evento foi exatamente o que o ADR-0006 evitou desde o início.

**`cronista` sem nenhum comando abre um menu inicial navegável** (ADR-0016, seção "segunda tentativa, funcionou"): banner + info de sessão, lista de comandos escolhida por seta. É Textual, mas só como seletor — ao escolher um item, o menu termina antes do comando escolhido rodar, exatamente como se o usuário tivesse digitado `cronista <comando>` direto. `rec` continua fora de qualquer loop de evento mesmo quando escolhido pelo menu. Fora de terminal interativo (script, pipe, CI), cai no mesmo conteúdo em texto estático — o menu não tenta abrir sem TTY.

## 2. Comandos

| Comando | O que faz | Precisa da API | UC |
|---|---|---|---|
| `cronista login` | Autentica e guarda os tokens | sim | UC-01 |
| `cronista devices` | Lista dispositivos de entrada e saída⁴ | **não** | UC-02 |
| `cronista rec` | Grava a reunião até interrupção | **não**¹ | UC-03 |
| `cronista importar <arquivo>` | Importa áudio ou vídeo existente | sim³ | UC-04 |
| `cronista sync` | Reenvia reuniões pendentes | sim | UC-11 |
| `cronista list` | Abre o painel navegável de reuniões² | sim | UC-07 |
| `cronista ler <id>` | Abre o painel já focado numa reunião² | sim | UC-07 |
| `cronista buscar <termo>` | Abre o painel com busca já preenchida² | sim | UC-08 |
| `cronista resumir <id>` | Gera um novo resumo | sim | UC-06 |
| `cronista reprocessar <id>` | Retranscreve, substituindo os segmentos antigos | sim | UC-05 (RF-15) |
| `cronista excluir <id>` | Remove reunião, com confirmação | sim | UC-09 |

¹ **`cronista rec` funciona com a API fora do ar.** Grava em disco e marca pendência, sem falhar. É a materialização do ADR-0012 na interface, e a razão de `cronista sync` existir.

² **`list`, `ler` e `buscar` são três portas de entrada para a mesma experiência navegável (ADR-0016), não três comandos independentes que imprimem e terminam.** Cada um abre o painel Textual num ponto de partida diferente — lista geral, uma reunião já aberta, ou busca já rodada — mas uma vez dentro, a navegação (setas, trocar de aba entre resumo/transcrição, nova busca) acontece na mesma tela, sem sair para rodar outro comando.

⁴ **`cronista devices` também abre numa tela persistente (Escape/q pra sair), gatilho de reversão do ADR-0016 disparado em 2026-09-04.** Diferente de `list`/`ler`/`buscar`, não é navegável — é só a lista de dispositivos, mostrada até o usuário sair. Fora de terminal interativo, cai no mesmo fallback de texto puro que já existia.

³ **`cronista importar` também tolera API fora do ar, mesmo padrão de `rec`¹.** Não por decisão à parte — ele reaproveita a mesma `registration.register()` que `rec` chama (UC-10 incluído por UC-04): converte e grava a trilha em disco, marca pendência se a API não confirmar, e `cronista sync` completa depois. "Sim" na coluna acima descreve o uso normal, não uma trava.

## 3. Comportamentos que o contrato garante

**`cronista rec` sem argumento nenhum grava.** Título e dispositivos são opcionais (RNF-U01). Título ausente é gerado a partir de data e hora.

**Durante a gravação, indicação de sinal por trilha** (RF-05). Sem isso, microfone mudo só é descoberto depois da reunião.

**Uma tecla pausa e retoma, sem encerrar** (RF-31). O tempo pausado não entra no arquivo (RN-11). O nome exato da tecla é detalhe de implementação, não fixado aqui.

**Encerramento por `Ctrl+C` é um caminho de sucesso, não de erro.** É como a gravação termina, pausada ou não.

**Renovação de token é silenciosa.** O usuário digita a senha em `cronista login` e não é interrompido de novo (UC-01, FA-01).

**Reconciliação é automática.** Qualquer comando que fale com a API verifica pendências. Em `cronista rec` isso acontece **depois** de encerrar a gravação, não antes de começar — rede nunca é pré-requisito pra iniciar ou manter uma captura (RN-08) — e só quando a própria reunião gravada agora confirmou com a API, pra não gastar tentativa sabendo que ela está fora. `cronista sync` existe pra forçar manualmente, a qualquer momento.

**`cronista excluir` sempre pede confirmação** e mostra o que será removido (UC-09).

## 4. Códigos de saída

| Código | Significado |
|---|---|
| `0` | Sucesso, inclui gravação encerrada por `Ctrl+C` e busca sem resultado |
| `1` | Erro de uso: argumento inválido, arquivo inexistente |
| `2` | Falha de autenticação |
| `3` | API inacessível **em operação que a exige** |
| `4` | Falha de dispositivo de áudio |
| `5` | Operação incompatível com o estado da reunião |

O código `3` nunca aparece em `cronista rec` nem em `cronista devices`, por construção.

## 5. Mensagens de erro

RNF-U02 e RNF-U03 exigem que a mensagem diga a ação corretiva e deixe claro **de quem** é a falha.

| Situação | Forma da mensagem |
|---|---|
| API fora durante `rec` | Informa que o áudio está salvo, onde está, e que o registro fica pendente. **Não é erro** |
| API fora em operação que exige | Aponta o serviço e sugere verificar o container |
| Provedor de LLM fora | Nomeia o provedor e como iniciá-lo |
| Loopback indisponível | Nomeia o dispositivo e adverte que a trilha `outros` não será gravada |
| Conversor ausente na importação | Nomeia a dependência e como instalá-la |

O padrão: **o que aconteceu, de quem é a falha, o que fazer**. Nunca só a exceção.

## 6. O que este documento não fixa

Nomes exatos de flag, formato das tabelas de saída, texto literal das mensagens. Isso se acerta melhor escrevendo e usando.

Aparência (cor, animação, barra de gradiente) é tratada à parte, em [17-identidade-visual-cli.md](17-identidade-visual-cli.md), para não misturar comportamento com apresentação.

**Ideias registradas para a Fase 5, não decididas ainda:** transcrição compacta por padrão (`voce: texto`, uma linha por fala) com verbosidade maior opcional por flag (timestamp em linha própria); saída estruturada (`--json`) em `list`/`buscar` para permitir scripting sobre o próprio acervo. Observadas no granola-cli durante pesquisa de referência; não viram requisito até a Fase 5 decidir se valem a pena.

O que está fixado é o que precisa ser decidido antes: quais comandos existem, **quais funcionam offline** e como o programa comunica falha.
