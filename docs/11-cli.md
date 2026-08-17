# Linha de Comando · Contrato

> **Versão:** 1.1 · **Última atualização:** 2026-08-17
> Decisões correspondentes: [0006](adr/0006-cli-antes-de-desktop.md), [0015](adr/0015-rich-como-apresentacao-cli.md)

## 1. Papel

A linha de comando é a primeira interface, e serve de contrato para a interface desktop que virá depois (Fase 8). Tudo que ela faz, faz chamando a API, exceto capturar áudio e listar dispositivos, que são locais por natureza.

O executável chama-se `cronista` ([16-nome.md](16-nome.md)).

## 2. Comandos

| Comando | O que faz | Precisa da API | UC |
|---|---|---|---|
| `cronista login` | Autentica e guarda os tokens | sim | UC-01 |
| `cronista devices` | Lista dispositivos de entrada e saída | **não** | UC-02 |
| `cronista rec` | Grava a reunião até interrupção | **não**¹ | UC-03 |
| `cronista importar <arquivo>` | Importa áudio ou vídeo existente | sim | UC-04 |
| `cronista sync` | Reenvia reuniões pendentes | sim | UC-11 |
| `cronista list` | Lista reuniões com estado | sim | UC-07 |
| `cronista ler <id>` | Mostra transcrição e resumos | sim | UC-07 |
| `cronista buscar <termo>` | Busca no acervo | sim | UC-08 |
| `cronista resumir <id>` | Gera um novo resumo | sim | UC-06 |
| `cronista excluir <id>` | Remove reunião, com confirmação | sim | UC-09 |

¹ **`cronista rec` funciona com a API fora do ar.** Grava em disco e marca pendência, sem falhar. É a materialização do ADR-0012 na interface, e a razão de `cronista sync` existir.

## 3. Comportamentos que o contrato garante

**`cronista rec` sem argumento nenhum grava.** Título e dispositivos são opcionais (RNF-U01). Título ausente é gerado a partir de data e hora.

**Durante a gravação, indicação de sinal por trilha** (RF-05). Sem isso, microfone mudo só é descoberto depois da reunião.

**Uma tecla pausa e retoma, sem encerrar** (RF-31). O tempo pausado não entra no arquivo (RN-11). O nome exato da tecla é detalhe de implementação, não fixado aqui.

**Encerramento por `Ctrl+C` é um caminho de sucesso, não de erro.** É como a gravação termina, pausada ou não.

**Renovação de token é silenciosa.** O usuário digita a senha em `cronista login` e não é interrompido de novo (UC-01, FA-01).

**Reconciliação é automática na inicialização.** Qualquer comando que fale com a API verifica pendências antes. `cronista sync` existe para forçar manualmente.

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

O que está fixado é o que precisa ser decidido antes: quais comandos existem, **quais funcionam offline** e como o programa comunica falha.
