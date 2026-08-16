# Requisitos

> **Versão:** 1.0 · **Última atualização:** 2026-08-12
> Deriva de [01-documento-de-visao.md](01-documento-de-visao.md). Rastreado em [06-matriz-rastreabilidade.md](06-matriz-rastreabilidade.md).

## Como ler

- **RF-nn** — requisito funcional: o que o sistema faz.
- **RNF-nn** — requisito não-funcional, classificado por **FURPS+**: com que qualidade ele faz.
- A coluna **Recurso** liga cada requisito ao recurso de produto (RP) que o originou.
- A coluna **Prioridade** usa: *Essencial* (sem ele não há produto), *Importante*, *Desejável*.

Requisito não descreve solução. Onde uma solução específica é obrigatória, ela está em ADR e é referenciada como restrição.

---

## 1. Requisitos funcionais

### 1.1 Captura de áudio

| ID | Requisito | Recurso | Prioridade |
|---|---|---|---|
| **RF-01** | Listar os dispositivos de entrada e de saída disponíveis, indicando quais serão usados por padrão | RP-01 | Essencial |
| **RF-02** | Gravar simultaneamente o microfone e o áudio de saída do sistema em **trilhas separadas** | RP-01, RP-02 | Essencial |
| **RF-03** | Persistir o áudio capturado em disco local **antes** de qualquer comunicação de rede | RP-01 | Essencial |
| **RF-04** | Encerrar a gravação por comando explícito do usuário | RP-01 | Essencial |
| **RF-05** | Exibir, durante a gravação, indicação de que há sinal em cada trilha | RP-01 | Importante |

> **RF-05 não é enfeite.** Sem ele, um microfone mudo ou um dispositivo de saída trocado só é descoberto depois da reunião, quando o áudio já se perdeu. É verificação em tempo de captura de uma falha irrecuperável.

### 1.2 Registro da reunião

| ID | Requisito | Recurso | Prioridade |
|---|---|---|---|
| **RF-06** | Registrar cada reunião com título, instante de início, instante de término, duração, origem (`gravação` ou `importação`) e máquina de origem | RP-01 | Essencial |
| **RF-07** | Associar à reunião as trilhas de áudio produzidas, referenciando-as por **caminho relativo** a uma raiz configurável | RP-01 | Essencial |
| **RF-08** | Reenviar automaticamente o registro de reuniões cuja persistência falhou, na execução seguinte | RP-01 | Essencial |
| **RF-09** | Aceitar arquivo de áudio ou vídeo preexistente como origem de uma reunião, convertendo-o ao formato interno | RP-05 | Desejável |

### 1.3 Transcrição

| ID | Requisito | Recurso | Prioridade |
|---|---|---|---|
| **RF-10** | Transcrever cada trilha de uma reunião produzindo segmentos com início, fim e texto | RP-03 | Essencial |
| **RF-11** | Atribuir falante a cada segmento a partir da trilha de origem | RP-02 | Essencial |
| **RF-12** | Mesclar as trilhas em uma transcrição única, ordenada cronologicamente | RP-03 | Essencial |
| **RF-13** | Aceitar vocabulário de domínio que oriente a transcrição de termos técnicos e nomes próprios | RP-03 | Importante |
| **RF-14** | Descartar trechos sem fala antes de transcrever | RP-03 | Importante |
| **RF-15** | Permitir reprocessar a transcrição de uma reunião já transcrita | RP-03 | Desejável |

> **RF-13 é onde o projeto se diferencia.** As ferramentas de mercado transcrevem português genérico. Vocabulário de domínio é o que separa "Coopmed" de "coopermed" e nomes de medicamentos de ruído fonético.

### 1.4 Resumo

| ID | Requisito | Recurso | Prioridade |
|---|---|---|---|
| **RF-16** | Gerar resumo estruturado contendo pauta, decisões, pendências com responsável e pontos em aberto | RP-04 | Essencial |
| **RF-17** | Processar transcrições maiores que a janela de contexto do modelo sem truncar conteúdo | RP-04 | Essencial |
| **RF-18** | Permitir escolher o provedor de modelo de linguagem por execução | RP-04 | Importante |
| **RF-19** | Preservar todos os resumos gerados para uma reunião, sem sobrescrever, registrando provedor e instante | RP-04 | Importante |

> **RF-19 existe para permitir comparação.** Trocar de modelo ou de prompt e perder o resultado anterior impede saber se houve melhora — e medir isso é o critério de sucesso do projeto.

### 1.5 Consulta

| ID | Requisito | Recurso | Prioridade |
|---|---|---|---|
| **RF-20** | Listar as reuniões registradas, com estado de processamento | RP-06 | Essencial |
| **RF-21** | Recuperar a transcrição completa de uma reunião | RP-06 | Essencial |
| **RF-22** | Recuperar os resumos de uma reunião | RP-06 | Essencial |
| **RF-23** | Buscar por conteúdo em todas as transcrições, com tratamento morfológico de português | RP-06 | Importante |
| **RF-24** | Indicar, em cada resultado de busca, a reunião, o instante e o falante | RP-06 | Importante |

### 1.6 Acesso e autenticação

| ID | Requisito | Recurso | Prioridade |
|---|---|---|---|
| **RF-25** | Autenticar por usuário e senha, emitindo token de acesso de validade curta e token de renovação | RP-07 | Essencial |
| **RF-26** | Renovar o token de acesso sem exigir nova apresentação de senha | RP-07 | Importante |
| **RF-27** | Exigir token válido em todas as operações, exceto na autenticação e na verificação de saúde do serviço | RP-07 | Essencial |
| **RF-28** | Armazenar a credencial apenas como hash, nunca em texto claro | RP-07 | Essencial |

### 1.7 Retenção

| ID | Requisito | Recurso | Prioridade |
|---|---|---|---|
| **RF-29** | Aplicar política de retenção ao áudio, por idade, preservando integralmente transcrição e resumos | RP-08 | Desejável |
| **RF-30** | Excluir uma reunião e todos os seus dados derivados, mediante confirmação | RP-08 | Desejável |

---

## 2. Requisitos não-funcionais (FURPS+)

### 2.1 Usabilidade

| ID | Requisito | Verificação |
|---|---|---|
| **RNF-U01** | Iniciar uma gravação exige um único comando, sem parâmetros obrigatórios | Manual |
| **RNF-U02** | Mensagens de erro em português, indicando a ação corretiva — não apenas a falha | Revisão |
| **RNF-U03** | O usuário consegue distinguir, na saída de erro, falha da própria máquina de falha de serviço externo | Revisão |

### 2.2 Confiabilidade

| ID | Requisito | Verificação |
|---|---|---|
| **RNF-R01** | **Nenhuma reunião é perdida** por indisponibilidade de API, banco de dados ou rede | Teste de injeção de falha |
| **RNF-R02** | Uma gravação em curso sobrevive à queda de qualquer componente que não seja o próprio processo de captura, e reconcilia o registro depois | Teste de injeção de falha |
| **RNF-R03** | Falha durante a transcrição não destrói o áudio, e o estado da reunião permite reprocessamento | Teste automatizado |
| **RNF-R04** | O acervo é recuperável a partir de rotina de backup documentada | Restauração de teste |

> **RNF-R01 é o requisito mais forte do sistema.** Áudio de reunião não se regrava: é a única falha irreversível. Ele é a origem de [adr/0012-gravacao-em-disco-antes-da-api.md](adr/0012-gravacao-em-disco-antes-da-api.md), e restringe deliberadamente a arquitetura escolhida.

### 2.3 Desempenho

| ID | Requisito | Verificação |
|---|---|---|
| **RNF-P01** | Transcrever mais rápido que o tempo real do áudio | Medição em reunião de 1h |
| **RNF-P02** | Busca textual responde em menos de 1 segundo no acervo previsto | Medição |
| **RNF-P03** | A captura não perde amostras enquanto o restante do sistema processa | Inspeção do áudio gravado |
| **RNF-P04** | A gravação não impede o uso normal da máquina durante a reunião | Manual |

> **RNF-P03 e RNF-P04 juntos** são o que impede a transcrição de rodar dentro do processo de captura: ocupar a GPU e a CPU durante a reunião violaria os dois.

### 2.4 Suportabilidade

| ID | Requisito | Verificação |
|---|---|---|
| **RNF-S01** | Toda decisão técnica relevante tem ADR com contexto, consequências e gatilho de reversão | Revisão |
| **RNF-S02** | Alterações de esquema do banco são versionadas e aplicáveis incrementalmente | Execução da migração |
| **RNF-S03** | O sistema registra em log o suficiente para diagnosticar falha de captura, de transcrição e de resumo sem reproduzir o problema | Revisão |
| **RNF-S04** | Trocar o provedor de modelo de linguagem não exige alterar código fora da camada de resumo | Revisão |

### 2.5 Restrições (+)

Herdadas de [01-documento-de-visao.md](01-documento-de-visao.md) §6, com a decisão que as concretiza.

| ID | Restrição | Tipo | ADR |
|---|---|---|---|
| **RNF-C01** | Nenhum áudio ou transcrição sai da máquina na configuração padrão | Legal/privacidade | 0002, 0005 |
| **RNF-C02** | Executa em Windows 11 | Física | 0001 |
| **RNF-C03** | A transcrição usa GPU local | Implementação | 0002 |
| **RNF-C04** | Custo recorrente zero na configuração padrão | Negócio | 0002, 0005 |
| **RNF-C05** | Interface e resumos em português brasileiro | Interface | — |
| **RNF-C06** | A API não é exposta à internet aberta | Segurança | 0011 |
| **RNF-C07** | O sistema não obtém nem verifica consentimento de gravação dos participantes; a responsabilidade é do usuário | Legal | — |

---

## 3. Requisitos explicitamente fora de escopo

Registrados para que não retornem como suposição implícita.

| Fora de escopo | Onde foi decidido |
|---|---|
| Múltiplos usuários, cadastro, recuperação de senha | Visão §8, ADR-0011 |
| Bot participante da chamada | Visão §8 |
| Transcrição exibida em tempo real durante a reunião | Visão §8 |
| Identificação nominal de cada participante na trilha `outros` | ADR-0001 — a trilha distingue "usuário × demais", não pessoa por pessoa |
| Tradução entre idiomas | Visão §8 |
| Aplicativo móvel | Visão §8 |
