# Plano de Testes

> **Versão:** 1.0 · **Última atualização:** 2026-08-12
> Rastreado em [06-matriz-rastreabilidade.md](06-matriz-rastreabilidade.md)

## 1. O que este plano precisa provar

Duas coisas distintas, e a segunda é a que justifica o projeto existir:

1. **Que o sistema funciona**: cobertura convencional dos casos de uso e, principalmente, dos fluxos de exceção.
2. **Que o resultado é melhor que a alternativa pronta.** O projeto foi construído sabendo que Meetily, Hyprnote e Fathom existem. A aposta é qualidade em português com vocabulário de domínio. Sem medir, isso é torcida.

## 2. Estratégia por camada

| Camada | Como testar | Automatizável |
|---|---|---|
| `core` (domínio, mesclagem, regras de estado) | Testes unitários com dados sintéticos | Sim |
| `api` | `TestClient`, banco de teste | Sim |
| `worker` | Unitário com áudio curto de referência | Sim |
| Busca | Integração contra PostgreSQL real | Sim |
| **Captura de áudio** | **Manual**, depende de hardware | Não |
| Qualidade de transcrição | Medição de WER contra referência | Semi |
| Qualidade de resumo | Rubrica manual comparativa | Não |

A captura não é automatizável de forma honesta: simular WASAPI testaria o simulador. Ela é validada por procedimento manual documentado (§6) e pela sondagem versionada em `scripts/check_audio.py`.

## 3. Casos de teste

### 3.1 Autenticação · Fase 1

| ID | Verifica |
|---|---|
| CT-01 | Credencial inválida responde 401, não grava token, e não distingue usuário inexistente de senha errada |
| CT-02 | Token de acesso expirado dispara renovação transparente e repete a operação |
| CT-03 | Token de renovação expirado força novo login |
| CT-04 | API inacessível não impede `devices` nem `rec` |
| CT-40 | Todo endpoint recusa requisição sem token, exceto login e saúde |
| CT-38 | Backup restaura o acervo em base limpa |
| CT-39 | Migração aplica do zero em base vazia |

### 3.2 Captura e envio · Fase 2

| ID | Verifica |
|---|---|
| CT-05 | Ausência de microfone é reportada com advertência sobre a trilha faltante |
| CT-06 | Saída sem loopback é reportada nomeando o dispositivo |
| CT-07 | Gravação produz dois WAV a 16 kHz mono, íntegros, com duração coerente |
| **CT-08** | **API derrubada durante a gravação: áudio íntegro em disco, pendência registrada, saída com sucesso** |
| CT-09 | Dispositivo removido no meio encerra a trilha afetada e mantém a outra |
| CT-10 | Disco cheio preserva o já gravado |
| CT-11 | Trilha sem sinal em todo o período gera advertência ao encerrar |
| CT-33 | Reconciliação envia pendências e limpa a marcação |
| CT-34 | Reconciliação com API ainda fora mantém a pendência, sem descarte |
| CT-35 | Envio interrompido reenvia apenas as trilhas faltantes |
| CT-41 | Pausar e retomar: o tempo pausado não aparece no arquivo final; áudio antes e depois da pausa fica contínuo |
| CT-42 | Dispositivo indisponível ao retomar de uma pausa: trilha afetada preservada, a outra continua se retomou normalmente |

**CT-08 é o caso de teste central do sistema.** Verifica ao mesmo tempo RNF-R01, RNF-R02, o fluxo FE-01 de UC-03 e a decisão do ADR-0012. Procedimento: iniciar gravação, derrubar o container da API no meio, encerrar a gravação, conferir que os WAV estão íntegros e reproduzíveis, que a pendência foi registrada e que o comando saiu com código 0. Depois subir a API e confirmar que `cronista sync` completa o registro.

### 3.3 Transcrição · Fase 3

| ID | Verifica |
|---|---|
| CT-16 | Reunião de 1 hora transcreve em menos de 1 hora (RNF-P01). **Medir separadamente o tempo de leitura das trilhas**: é o custo da fronteira 9P e o gatilho de reversão do [ADR-0014](adr/0014-worker-em-container-com-gpu.md) |
| CT-17 | Segmentos das duas trilhas saem mesclados em ordem, com falante correto |
| CT-18 | Memória insuficiente marca falha e **preserva o áudio** |
| CT-19 | Worker interrompido devolve a reunião à fila na inicialização seguinte |
| CT-20 | Reprocessar substitui segmentos anteriores sem duplicar |
| CT-36 | WER medido contra transcrição de referência |

### 3.4 Resumo · Fase 4

| ID | Verifica |
|---|---|
| CT-21 | Resumo contém as quatro seções, com responsável nas pendências |
| CT-22 | Transcrição maior que a janela é processada sem truncar |
| CT-23 | Provedor fora do ar reporta qual e como iniciar, sem gravar resumo parcial |
| CT-24 | Gerar resumo de novo acrescenta registro, não sobrescreve |
| CT-37 | Rubrica comparativa entre provedores |

### 3.5 Consulta, busca e retenção · Fases 5 e 7

| ID | Verifica |
|---|---|
| CT-25 | Listagem e consulta devolvem estado, transcrição e resumos |
| CT-26 | Reunião ainda em processamento é consultável sem erro |
| CT-27 | Busca por "decisão" encontra "decidimos", stemming de português |
| CT-28 | Busca responde em menos de 1 segundo |
| CT-29 | Busca sem resultado devolve lista vazia, não erro |
| CT-30 | Retenção não remove áudio de reunião ainda não transcrita |
| CT-31 | Exclusão remove segmentos, resumos e arquivos |
| CT-32 | Exclusão sem confirmação não remove nada |

### 3.6 Importação · Fase 6

| ID | Verifica |
|---|---|
| CT-12 | Arquivo de áudio vira reunião com trilha única |
| CT-13 | Formato não suportado é reportado com a lista de aceitos |
| CT-14 | Origem em vídeo tem a faixa de áudio extraída |
| CT-15 | Conversor ausente reporta a dependência e como instalar |

## 4. Medição de transcrição · CT-36

**Material.** Uma reunião real em português, de 20 a 30 minutos, com vocabulário do domínio e ao menos dois participantes. Transcrita manualmente uma vez, com cuidado, para servir de referência. Esse trabalho é feito uma vez e reaproveitado sempre.

**Métrica.** WER: proporção de inserções, remoções e substituições sobre a referência.

**Três medições sobre o mesmo áudio:**

| Configuração | O que responde |
|---|---|
| Sem vocabulário de domínio | Linha de base |
| Com vocabulário de domínio | **Quanto RF-13 realmente entrega** |
| Ferramenta de mercado, se acessível | Onde o projeto está frente ao pronto |

A comparação entre as duas primeiras é a que importa: é a única evidência de que o diferencial do projeto existe. Se o ganho for irrelevante, isso precisa ser sabido cedo, e registrado.

## 5. Avaliação de resumo · CT-37

Não há métrica automática confiável para qualidade de resumo. A avaliação é manual, por rubrica, sobre a **mesma reunião**.

| Critério | Pergunta | Peso |
|---|---|---|
| Decisões | Todas as decisões reais aparecem? Alguma inventada? | Alto |
| Pendências | Cada ação tem responsável identificado corretamente? | Alto |
| Alucinação | Há alguma afirmação que não ocorreu na reunião? | **Eliminatório** |
| Cobertura | Algum assunto relevante ficou de fora? | Médio |
| Concisão | Repete a transcrição ou de fato sintetiza? | Médio |
| Português | Texto natural, sem estrangeirismo estranho? | Médio |

**Alucinação é eliminatória.** Um resumo que inventa uma decisão é pior que resumo nenhum, porque será lido como verdade e ninguém vai reconferir a gravação.

**Comparação obrigatória:** Ollama local × Claude × Notion AI, sobre a mesma reunião. É esta tabela que responde se o projeto valeu a pena, e ela deve ser publicada no README, inclusive se o resultado for desfavorável.

## 6. Procedimento manual de captura

Executado a cada mudança na camada de captura:

1. `cronista devices`: conferir que microfone e saída aparecem, e que a saída oferece loopback.
2. `cronista rec` durante uma chamada real de 2 minutos, falando e ouvindo o outro lado.
3. Conferir que os dois WAV existem, têm duração coerente e são reproduzíveis.
4. Confirmar que `voce.wav` tem a sua voz e `outros.wav` tem a do interlocutor, **não o contrário**.
5. Conferir que o indicador de sinal se moveu nas duas trilhas durante a gravação.

O passo 4 é o que detecta trilhas trocadas, defeito que passaria despercebido em qualquer teste automatizado e corromperia todos os resumos.

## 7. Ambiente de teste

| Item | Configuração |
|---|---|
| Banco | Instância PostgreSQL separada, recriada por execução |
| Áudio de referência | Versionado fora do repositório principal, por tamanho |
| Provedor de LLM | Ollama local; provedor remoto apenas em CT-37 |
| GPU | Testes de transcrição exigem a máquina real |

## 8. Critério de pronto por fase

Uma fase só está concluída quando **todos os seus casos de teste passam**, incluindo os de exceção. Os critérios estão em [15-roadmap.md](15-roadmap.md).

Regra que vale para todas: **nenhuma fase é dada por concluída com um teste de exceção falhando.** São eles que descrevem o comportamento sob falha, e falha é o que efetivamente acontece em uso real.
