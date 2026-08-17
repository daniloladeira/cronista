# Detalhamento dos Casos de Uso

> **Versão:** 1.0 · **Última atualização:** 2026-08-12
> Atores e diagrama em [04-modelo-de-casos-de-uso.md](04-modelo-de-casos-de-uso.md). Requisitos em [03-requisitos.md](03-requisitos.md).

## Convenções

- **FP**: fluxo principal · **FA**: fluxo alternativo · **FE**: fluxo de exceção · **RN**: regra de negócio
- Estados da reunião: `gravando`, `pendente_envio`, `gravada`, `transcrevendo`, `transcrita`, `resumida`, e os de falha `falha_envio`, `falha_transcricao`, `falha_resumo`
- "Cliente" designa o processo local de captura e linha de comando; "API" designa o serviço; "Worker" designa o processo de transcrição

---

## Regras de negócio

Aplicam-se a mais de um caso de uso e por isso ficam centralizadas.

| ID | Regra |
|---|---|
| **RN-01** | A trilha do microfone é sempre atribuída ao falante `voce`; a trilha de loopback, ao falante `outros`. A atribuição vem da origem do sinal, nunca de análise do conteúdo |
| **RN-02** | Arquivo importado produz uma única trilha, com falante `desconhecido` |
| **RN-03** | Resumos nunca são sobrescritos. Cada geração cria um novo registro, com provedor e instante |
| **RN-04** | A política de retenção afeta **apenas áudio**. Transcrição e resumos são permanentes até exclusão explícita da reunião |
| **RN-05** | Excluir uma reunião remove em cascata seus segmentos, resumos e arquivos de áudio |
| **RN-06** | Uma reunião só entra em transcrição a partir de `gravada` ou `falha_transcricao` |
| **RN-07** | Um resumo só pode ser gerado a partir de `transcrita` ou `resumida` |
| **RN-08** | O áudio é gravado em disco local **antes** de qualquer chamada de rede. Registro remoto nunca é pré-requisito para iniciar ou manter uma gravação |
| **RN-09** | O formato interno de áudio é WAV PCM 16 bits, 16 kHz, mono, um arquivo por trilha |
| **RN-10** | Toda operação da API exige token válido, exceto autenticação e verificação de saúde |

---

## UC-01 · Autenticar-se

| | |
|---|---|
| **Ator primário** | Usuário |
| **Requisitos** | RF-25, RF-26, RF-27, RF-28 |
| **Pré-condições** | A API está acessível |
| **Pós-condições** | O cliente possui token de acesso válido e token de renovação armazenados localmente |

**FP**
1. O usuário solicita autenticação informando usuário e senha.
2. O cliente envia as credenciais à API.
3. A API compara a senha com o hash armazenado.
4. A API emite token de acesso de validade curta e token de renovação.
5. O cliente armazena os tokens no perfil do usuário do sistema operacional.

**FA-01. Renovação automática.** Em qualquer operação, se o token de acesso estiver expirado e houver token de renovação válido, o cliente renova de forma transparente e repete a operação original, sem pedir senha.

**FE-01. Credencial inválida.** A API responde 401. O cliente informa que usuário ou senha estão incorretos, sem distinguir qual, para não revelar a existência do usuário. Nenhum token é gravado.

**FE-02. Token de renovação expirado.** O cliente descarta os tokens e solicita autenticação completa.

**FE-03. API inacessível.** O cliente informa que o serviço não respondeu e indica a verificação do container. Comandos que operam offline (UC-02, UC-03) permanecem disponíveis.

**Requisitos especiais.** A senha nunca é registrada em log nem gravada em disco. O armazenamento do token segue [10-autenticacao.md](10-autenticacao.md).

---

## UC-02 · Listar dispositivos de áudio

| | |
|---|---|
| **Ator primário** | Usuário · **Apoio:** Dispositivo de Áudio |
| **Requisitos** | RF-01 |
| **Pré-condições** | Nenhuma. **Opera offline** |
| **Pós-condições** | Nenhuma alteração de estado |

**FP**
1. O usuário solicita a lista de dispositivos.
2. O cliente consulta o subsistema de áudio do sistema operacional.
3. O cliente apresenta os dispositivos de entrada e de saída, destacando os padrões e indicando qual saída será usada para loopback.

**FE-01. Nenhum dispositivo de entrada.** O cliente informa que não há microfone disponível e adverte que a gravação capturaria apenas a trilha `outros`.

**FE-02. Loopback indisponível na saída padrão.** O cliente informa que o dispositivo de saída não expõe captura de loopback e sugere selecionar outro. Sem loopback não há trilha `outros`, o que inviabiliza o propósito da gravação.

---

## UC-03 · Gravar reunião

| | |
|---|---|
| **Ator primário** | Usuário · **Apoio:** Dispositivo de Áudio |
| **Requisitos** | RF-02 a RF-08 |
| **Inclui** | UC-10 |
| **Pré-condições** | Existe dispositivo de entrada e dispositivo de saída com loopback. **Não exige API disponível** (RN-08) |
| **Pós-condições** | Dois arquivos WAV em disco local; reunião registrada, ou marcada como `pendente_envio` |

**FP**
1. O usuário inicia a gravação, opcionalmente informando um título.
2. O cliente cria o diretório da reunião no disco local.
3. O cliente abre a captura do microfone e a captura de loopback da saída, ambas em 16 kHz mono (RN-09).
4. O cliente grava as duas trilhas simultaneamente em arquivos separados, estado `gravando`.
5. O cliente exibe continuamente indicação de sinal de cada trilha (RF-05).
6. O usuário encerra a gravação.
7. O cliente fecha os arquivos e calcula a duração.
8. **Inclui UC-10** para registrar a reunião e as trilhas.
9. O cliente informa a localização dos arquivos e o identificador da reunião.

**FA-01. Sem título.** Não informado título, o cliente gera um a partir da data e hora de início. O usuário pode renomear depois.

**FA-02. Dispositivo explícito.** O usuário indica dispositivo de entrada ou de saída diferente do padrão; o cliente usa o indicado.

**FE-01. API indisponível no passo 8.** *Este é o fluxo de exceção mais importante do sistema.* Os arquivos de áudio já estão íntegros em disco. O cliente registra a reunião localmente como `pendente_envio`, informa ao usuário que o áudio está salvo e que o registro será concluído depois, e **encerra com sucesso**. A recuperação ocorre em UC-11. Atende RNF-R01 e RNF-R02.

**FE-02. Dispositivo desaparece durante a gravação.** Situação real: fone desconectado no meio da reunião. O cliente encerra a trilha afetada preservando o que foi gravado, alerta o usuário de forma visível e **continua gravando a outra trilha**. A reunião prossegue com trilha única.

**FE-03. Disco sem espaço.** O cliente interrompe a gravação, preserva o que já foi escrito, e informa o espaço necessário. O material parcial permanece utilizável.

**FE-04. Sinal ausente em uma trilha durante todo o período.** Ao encerrar, o cliente adverte que a trilha não registrou sinal e sugere verificar o dispositivo. Não impede o registro: o áudio existente continua válido.

**Requisitos especiais.** A captura escreve em disco de forma incremental, não acumulando a reunião em memória (RNF-P03). O processamento durante a gravação limita-se ao necessário para escrever e medir sinal (RNF-P04).

---

## UC-04 · Importar arquivo de áudio

| | |
|---|---|
| **Ator primário** | Usuário |
| **Requisitos** | RF-09 |
| **Inclui** | UC-10 |
| **Pré-condições** | Arquivo de áudio ou vídeo acessível; ferramenta de conversão disponível |
| **Pós-condições** | Reunião registrada com uma trilha convertida ao formato interno |

**FP**
1. O usuário indica o arquivo e, opcionalmente, um título.
2. O cliente verifica que o formato é suportado.
3. O cliente converte o áudio para o formato interno (RN-09), extraindo a faixa de áudio quando a origem é vídeo.
4. O cliente cria o diretório da reunião e grava a trilha convertida, com falante `desconhecido` (RN-02).
5. **Inclui UC-10**, registrando a reunião com origem `importação`.

**FA-01. Origem em vídeo.** O cliente extrai apenas a faixa de áudio; o vídeo é descartado.

**FE-01. Formato não suportado ou arquivo corrompido.** O cliente informa o formato detectado e a lista de formatos aceitos. Nada é registrado.

**FE-02. Arquivo sem faixa de áudio.** O cliente informa e interrompe.

**FE-03. Ferramenta de conversão ausente.** O cliente informa a dependência faltante e como instalá-la.

**Regras.** RN-02: a ausência de separação por trilha significa que este caminho não distingue falantes. Elevar isso exigiria diarização, decisão adiada e registrada em [adr/0007-fonte-de-audio-plugavel.md](adr/0007-fonte-de-audio-plugavel.md).

---

## UC-05 · Transcrever reunião

| | |
|---|---|
| **Ator primário** | Agendador |
| **Requisitos** | RF-10 a RF-15 |
| **Estendido por** | UC-06 (resumo automático, condicional) |
| **Pré-condições** | Reunião em `gravada` ou `falha_transcricao` (RN-06); arquivos de áudio presentes; GPU disponível |
| **Pós-condições** | Segmentos persistidos com falante e marcação de tempo; reunião em `transcrita` |

**FP**
1. O worker seleciona a reunião mais antiga em estado elegível.
2. O worker marca a reunião como `transcrevendo`.
3. Para **cada trilha** da reunião, uma lista, não um número fixo:
   1. descarta trechos sem fala;
   2. transcreve o áudio produzindo segmentos com início, fim e texto;
   3. atribui o falante conforme a origem da trilha (RN-01, RN-02).
4. O worker mescla os segmentos de todas as trilhas em ordem cronológica.
5. O worker persiste os segmentos e marca a reunião como `transcrita`.

**FA-01. Vocabulário de domínio configurado.** O worker fornece o vocabulário ao modelo como contexto inicial, melhorando termos técnicos e nomes próprios (RF-13).

**FA-02. Reprocessamento.** Solicitada nova transcrição de reunião já transcrita, o worker remove os segmentos anteriores antes de persistir os novos. Resumos existentes são preservados e passam a referir-se a uma transcrição substituída, condição registrada no resumo.

**FA-03. Trilha silenciosa.** Trilha sem fala detectada produz zero segmentos e não interrompe o processamento das demais.

**FE-01. Memória de vídeo insuficiente.** O worker tenta uma vez com configuração de menor consumo. Persistindo a falha, marca `falha_transcricao` com a causa. **O áudio permanece intacto** e a reunião continua elegível a reprocessamento (RNF-R03).

**FE-02. Arquivo de áudio ausente ou ilegível.** O worker marca `falha_transcricao` registrando o caminho esperado. Não remove o registro da reunião.

**FE-03. Worker interrompido durante o processamento.** A reunião permanece em `transcrevendo` sem worker ativo. Na inicialização seguinte, o worker devolve ao estado elegível reuniões nessa condição. Nenhum trabalho se perde além do processamento já gasto.

**FE-04. Banco indisponível ao persistir.** O worker mantém a reunião no estado anterior e repete depois. O áudio não é afetado.

**Requisitos especiais.** RNF-P01: a transcrição deve ser mais rápida que o tempo real do áudio. O worker executa em processo separado da API, pois mantém o modelo carregado em memória de vídeo ([07-arquitetura.md](07-arquitetura.md)).

---

## UC-06 · Gerar resumo

| | |
|---|---|
| **Ator primário** | Usuário · **Apoio:** Provedor de LLM |
| **Requisitos** | RF-16 a RF-19 |
| **Estende** | UC-05 |
| **Pré-condições** | Reunião em `transcrita` ou `resumida` (RN-07); provedor de LLM acessível |
| **Pós-condições** | Novo resumo persistido, sem substituir os anteriores (RN-03) |

**FP**
1. O usuário solicita o resumo de uma reunião.
2. A API recupera a transcrição completa, com falantes e marcação de tempo.
3. A API seleciona o provedor configurado.
4. A API submete a transcrição ao modelo com o prompt versionado vigente.
5. O modelo devolve resumo estruturado: pauta, decisões, pendências com responsável e pontos em aberto.
6. A API persiste o resumo registrando provedor, versão do prompt e instante.
7. A API devolve o resumo ao usuário.

**FA-01. Transcrição maior que a janela de contexto.** A API divide a transcrição, resume cada parte e consolida os resultados, preservando todo o conteúdo sem truncar (RF-17).

**FA-02. Provedor alternativo.** O usuário indica provedor diferente do padrão. O resumo é gerado por ele e o registro identifica qual foi usado, permitindo comparação (RF-18, RF-19).

**FA-03. Disparo automático.** Configurado para tal, a conclusão de UC-05 dispara este caso de uso sem intervenção do usuário.

**FE-01. Provedor de LLM indisponível.** Situação corriqueira: o Ollama não está em execução. A API responde informando qual provedor falhou e como iniciá-lo. A reunião permanece em `transcrita`, e nenhum resumo parcial é gravado.

**FE-02. Resposta fora do formato esperado.** A API registra a resposta bruta para diagnóstico e informa a falha. Não persiste resumo malformado como se fosse válido.

**FE-03. Reunião sem segmentos.** A API recusa a operação informando que não há transcrição a resumir.

**FE-04. Tempo limite excedido.** A API encerra a espera, informa e mantém a reunião elegível a nova tentativa.

---

## UC-07 · Consultar reunião

| | |
|---|---|
| **Ator primário** | Usuário |
| **Requisitos** | RF-20, RF-21, RF-22 |
| **Pré-condições** | Autenticado (RN-10) |
| **Pós-condições** | Nenhuma alteração de estado |

**FP**
1. O usuário solicita a lista de reuniões.
2. A API devolve as reuniões com título, data, duração, origem e estado de processamento.
3. O usuário seleciona uma reunião.
4. A API devolve os dados da reunião, a transcrição com falantes e marcação de tempo, e os resumos existentes.

**FA-01. Somente resumo.** O usuário solicita apenas o resumo; a transcrição completa não é transferida.

**FA-02. Múltiplos resumos.** Havendo mais de um resumo, todos são devolvidos em ordem cronológica decrescente, identificados por provedor, o que permite compará-los (RF-19).

**FA-03. Reunião ainda em processamento.** A API devolve o estado atual e o que já existe, sem erro.

**FE-01. Reunião inexistente.** Resposta 404.

**FE-02. Token ausente ou expirado.** Resposta 401. O cliente aplica FA-01 de UC-01 e repete.

---

## UC-08 · Buscar em reuniões

| | |
|---|---|
| **Ator primário** | Usuário |
| **Requisitos** | RF-23, RF-24 |
| **Estende** | UC-07 |
| **Pré-condições** | Autenticado; existe ao menos uma reunião transcrita |
| **Pós-condições** | Nenhuma alteração de estado |

**FP**
1. O usuário informa termos de busca.
2. A API consulta os segmentos aplicando tratamento morfológico de português: variações da mesma raiz são equivalentes.
3. A API devolve os trechos encontrados, cada um com reunião de origem, instante, falante e texto.
4. O usuário pode abrir a reunião de um resultado (**estende UC-07**).

**FA-01. Filtro por período ou falante.** O usuário restringe a busca; a API aplica o filtro antes de ordenar por relevância.

**FA-02. Nenhum resultado.** A API devolve lista vazia; o cliente informa que nada foi encontrado, sem tratar como erro.

**FE-01. Expressão de busca inválida.** A API informa o problema na expressão em vez de devolver erro genérico.

**Requisitos especiais.** RNF-P02: resposta em menos de 1 segundo. O tratamento morfológico de português é requisito, não otimização: sem ele, buscar "decisão" não encontra "decidimos", e o acervo perde utilidade.

---

## UC-09 · Aplicar retenção e excluir reunião

| | |
|---|---|
| **Ator primário** | Agendador (retenção) e Usuário (exclusão) |
| **Requisitos** | RF-29, RF-30 |
| **Pré-condições** | Política de retenção configurada |
| **Pós-condições** | Áudio antigo comprimido ou removido; ou reunião integralmente removida |

**FP, Retenção (Agendador)**
1. O agendador seleciona reuniões cujo áudio excedeu o prazo configurado e que já estejam transcritas.
2. Conforme a política, comprime o áudio ou o remove.
3. Atualiza o registro indicando que o áudio não está mais no formato original.
4. Transcrição e resumos permanecem intactos (RN-04).

**FP, Exclusão (Usuário)**
1. O usuário solicita a exclusão de uma reunião.
2. A API apresenta o que será removido e solicita confirmação explícita.
3. Confirmado, a API remove segmentos, resumos, registro e arquivos de áudio (RN-05).

**FA-01. Reunião não transcrita.** A retenção **não** remove áudio de reunião ainda não transcrita, qualquer que seja a idade: remover destruiria o único dado existente.

**FE-01. Exclusão não confirmada.** Nada é removido.

**FE-02. Arquivo de áudio já ausente.** A operação prossegue e conclui com sucesso, registrando a ausência. Remoção é idempotente.

**FE-03. Falha ao remover arquivo.** A API não remove o registro do banco, evitando referência órfã, e informa a falha.

---

## UC-10 · Enviar trilha de áudio

*Caso de uso incluído. Não é iniciado diretamente pelo usuário.*

| | |
|---|---|
| **Incluído por** | UC-03, UC-04, UC-11 |
| **Requisitos** | RF-06, RF-07 |
| **Pré-condições** | Existe ao menos uma trilha íntegra em disco local |
| **Pós-condições** | Reunião e trilhas registradas; estado `gravada` |

**FP**
1. O cliente registra a reunião na API com título, instantes, duração, origem e máquina.
2. A API cria a reunião em estado `registering` (existe no banco, trilhas ainda pendentes) e devolve o identificador.
3. Para cada trilha, o cliente envia o arquivo associando-o à reunião e ao falante correspondente.
4. A API armazena a referência da trilha por caminho relativo (RF-07).
5. Confirmadas todas as trilhas, a API marca a reunião como `gravada` (`recorded`), tornando-a elegível a UC-05.

**FA-01. Reunião já registrada.** Em reprocessamento por UC-11, o cliente reaproveita o identificador existente (a reunião já pode estar em `registering`, se o passo 2 já tinha sido concluído antes) em vez de criar duplicata.

**FE-01. API indisponível.** O cliente marca a reunião local como `pendente_envio` e encerra sem erro. A recuperação é responsabilidade de UC-11.

**FE-02. Falha no meio do envio das trilhas.** A reunião já existe no banco em `registering`, mas com trilhas incompletas. O cliente marca a pendência local como `falha_envio`, distinta de `pendente_envio` porque o identificador da reunião já existe. UC-11 reenvia apenas as trilhas faltantes.

**FE-03. Trilha excede o limite aceito.** A API informa o limite. O cliente mantém o arquivo local e reporta, sem descartá-lo.

**Requisitos especiais.** O envio é sempre posterior à gravação completa em disco (RN-08). Este caso de uso jamais é pré-requisito para iniciar ou manter uma captura.

---

## UC-11 · Reconciliar reuniões pendentes

| | |
|---|---|
| **Ator primário** | Agendador |
| **Requisitos** | RF-08 |
| **Inclui** | UC-10 |
| **Pré-condições** | Existem reuniões locais em `pendente_envio` ou `falha_envio` |
| **Pós-condições** | Reuniões pendentes registradas na API, ou mantidas pendentes para nova tentativa |

**FP**
1. Na inicialização do cliente, ou periodicamente, o agendador verifica reuniões locais pendentes.
2. Para cada uma, verifica a integridade dos arquivos de áudio.
3. **Inclui UC-10** para concluir o registro.
4. Concluído com sucesso, remove a marcação de pendência local.
5. Informa ao usuário quantas reuniões foram reconciliadas.

**FA-01. Nenhuma pendência.** Encerra silenciosamente, sem saída.

**FE-01. API ainda indisponível.** Mantém a pendência e encerra sem erro. Repetirá na próxima oportunidade. Não há descarte por número de tentativas: o áudio é insubstituível e a espera não tem custo.

**FE-02. Arquivo de áudio de uma pendência não existe mais.** Registra a inconsistência e informa o usuário, mas **não remove** a pendência automaticamente: a remoção exige decisão humana.

**Requisitos especiais.** Este caso de uso existe exclusivamente para satisfazer RNF-R01. Ele é o par obrigatório de FE-01 de UC-03: sem ele, a gravação sobreviveria à queda da API mas o registro nunca se completaria.
