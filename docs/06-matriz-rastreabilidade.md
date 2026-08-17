# Matriz de Rastreabilidade

> **Versão:** 1.0 · **Última atualização:** 2026-08-12

Este documento é a verificação da especificação. Ele existe para responder quatro perguntas com prova, não com impressão:

1. Todo recurso de produto virou requisito?
2. Todo requisito tem comportamento definido em algum caso de uso?
3. Todo caso de uso tem lugar no roadmap?
4. Todo fluxo de exceção tem caso de teste?

Uma lacuna em qualquer eixo é defeito de especificação, e é aqui que ela aparece.

---

## 1. Recurso de produto → requisitos

| Recurso | Requisitos | Cobertura |
|---|---|---|
| RP-01 Gravação sem bot | RF-01 a RF-08 | sim |
| RP-02 Separação de quem falou | RF-02, RF-11 | sim |
| RP-03 Transcrição local | RF-10, RF-12 a RF-15 | sim |
| RP-04 Resumo estruturado | RF-16 a RF-19 | sim |
| RP-05 Importação de áudio | RF-09 | sim |
| RP-06 Consulta e busca | RF-20 a RF-24 | sim |
| RP-07 Acesso autenticado | RF-25 a RF-28 | sim |
| RP-08 Retenção configurável | RF-29, RF-30 | sim |

Nenhum recurso sem requisito. Nenhum requisito funcional órfão de recurso.

---

## 2. Requisito → caso de uso → fase → teste

| RF | Caso de uso | Fase | Casos de teste |
|---|---|---|---|
| RF-01 | UC-02 | 2 | CT-05, CT-06 |
| RF-02 | UC-03 | 2 | CT-07 |
| RF-03 | UC-03 | 2 | CT-07, CT-08 |
| RF-04 | UC-03 | 2 | CT-07 |
| RF-05 | UC-03 | 2 | CT-11 |
| RF-06 | UC-10 | 2 | CT-07, CT-35 |
| RF-07 | UC-10 | 2 | CT-07 |
| RF-08 | UC-11 | 2 | CT-33, CT-34, CT-35 |
| RF-09 | UC-04 | 6 | CT-12, CT-13, CT-14, CT-15 |
| RF-10 | UC-05 | 3 | CT-16, CT-36 |
| RF-11 | UC-05 | 3 | CT-17 |
| RF-12 | UC-05 | 3 | CT-17 |
| RF-13 | UC-05 | 3 | CT-36 |
| RF-14 | UC-05 | 3 | CT-16 |
| RF-15 | UC-05 | 3 | CT-20 |
| RF-16 | UC-06 | 4 | CT-21, CT-37 |
| RF-17 | UC-06 | 4 | CT-22 |
| RF-18 | UC-06 | 4 | CT-37 |
| RF-19 | UC-06 | 4 | CT-24 |
| RF-20 | UC-07 | 5 | CT-25, CT-26 |
| RF-21 | UC-07 | 5 | CT-25 |
| RF-22 | UC-07 | 5 | CT-24 |
| RF-23 | UC-08 | 5 | CT-27 |
| RF-24 | UC-08 | 5 | CT-27 |
| RF-25 | UC-01 | 1 | CT-01 |
| RF-26 | UC-01 | 1 | CT-02, CT-03 |
| RF-27 | UC-01 | 1 | CT-40 |
| RF-28 | UC-01 | 1 | CT-01 |
| RF-29 | UC-09 | 7 | CT-30 |
| RF-30 | UC-09 | 7 | CT-31, CT-32 |

**30 requisitos funcionais, 30 cobertos.** Nenhum requisito sem caso de uso, sem fase ou sem teste.

---

## 3. Requisitos não-funcionais → verificação

| RNF | Como se verifica | Caso de teste | Fase |
|---|---|---|---|
| RNF-U01 Um comando para gravar | Inspeção da interface | — | 2 |
| RNF-U02 Erro em português e acionável | Revisão das mensagens | CT-15, CT-23 | 2+ |
| RNF-U03 Distinguir falha local de externa | Revisão das mensagens | CT-04, CT-23 | 2+ |
| **RNF-R01 Nenhuma reunião perdida** | **Injeção de falha** | **CT-08, CT-33, CT-34** | **2** |
| RNF-R02 Gravação sobrevive e reconcilia | Injeção de falha | CT-08, CT-33 | 2 |
| RNF-R03 Falha de transcrição preserva áudio | Automatizado | CT-18, CT-19 | 3 |
| RNF-R04 Acervo recuperável | Restauração de teste | CT-38 | 1 |
| RNF-P01 Mais rápido que tempo real | Medição em reunião de 1h | CT-16 | 3 |
| RNF-P02 Busca sob 1 segundo | Medição | CT-28 | 5 |
| RNF-P03 Captura não perde amostra | Inspeção do áudio | CT-07 | 2 |
| RNF-P04 Máquina utilizável durante gravação | Observação manual | — | 2 |
| RNF-S01 Decisões em ADR | Revisão | seção 5 | 1 |
| RNF-S02 Migração versionada | Execução da migração | CT-39 | 1 |
| RNF-S03 Log suficiente para diagnóstico | Revisão | — | 3 |
| RNF-S04 Trocar provedor sem tocar fora da camada | Revisão de código | CT-37 | 4 |
| RNF-C01 Nada sai da máquina no padrão | Inspeção de tráfego | — | 4 |
| RNF-C02 a RNF-C07 | Restrições — verificadas por revisão | — | — |

---

## 4. Fluxo de exceção → caso de teste

Os fluxos de exceção são a parte da especificação com maior chance de virar defeito, porque descrevem o que ninguém exercita no uso feliz. Todos têm teste.

| Origem | Fluxo | Caso de teste |
|---|---|---|
| UC-01 | FE-01 credencial inválida | CT-01 |
| UC-01 | FE-02 renovação expirada | CT-03 |
| UC-01 | FE-03 API inacessível | CT-04 |
| UC-02 | FE-01 sem microfone | CT-05 |
| UC-02 | FE-02 loopback indisponível | CT-06 |
| **UC-03** | **FE-01 API cai durante a gravação** | **CT-08** |
| UC-03 | FE-02 dispositivo removido no meio | CT-09 |
| UC-03 | FE-03 disco sem espaço | CT-10 |
| UC-03 | FE-04 trilha sem sinal | CT-11 |
| UC-04 | FE-01 formato não suportado | CT-13 |
| UC-04 | FE-03 conversor ausente | CT-15 |
| UC-05 | FE-01 memória de vídeo insuficiente | CT-18 |
| UC-05 | FE-03 worker interrompido | CT-19 |
| UC-06 | FE-01 provedor de LLM fora do ar | CT-23 |
| UC-07 | FE-02 token expirado | CT-02 |
| UC-08 | FA-02 busca sem resultado | CT-29 |
| UC-09 | FA-01 retenção poupa não transcrita | CT-30 |
| UC-09 | FE-01 exclusão não confirmada | CT-32 |
| UC-10 | FE-02 envio parcial | CT-35 |
| UC-11 | FE-01 API ainda indisponível | CT-34 |

**CT-08 é o caso de teste central do sistema.** Ele verifica simultaneamente RNF-R01, RNF-R02, o fluxo FE-01 de UC-03 e a decisão registrada no ADR-0012. Se apenas um teste pudesse existir, seria ele.

---

## 5. Decisão → ADR

| Decisão | ADR | Requisitos que a motivam |
|---|---|---|
| Captura local em duas trilhas, sem diarização | [0001](adr/0001-captura-local-duas-trilhas.md) | RF-02, RF-11, RNF-C02 |
| Transcrição local em GPU | [0002](adr/0002-faster-whisper-local.md) | RNF-C01, RNF-C03, RNF-C04, RNF-P01 |
| PostgreSQL como banco | [0003](adr/0003-postgres-como-banco.md) | RF-23, RNF-P02 |
| UUIDv7, timestamptz, caminhos relativos | [0004](adr/0004-uuid-timestamptz-caminhos-relativos.md) | RF-07 |
| LangChain na camada de resumo | [0005](adr/0005-langchain-na-camada-de-resumo.md) | RF-18, RNF-S04 |
| CLI antes de desktop | [0006](adr/0006-cli-antes-de-desktop.md) | RNF-U01 |
| Fonte de áudio plugável | [0007](adr/0007-fonte-de-audio-plugavel.md) | RF-09, RN-02 |
| Python 3.13 | [0008](adr/0008-python-313.md) | RNF-C03 |
| SQLAlchemy e Alembic | [0009](adr/0009-sqlalchemy-alembic.md) | RNF-S02 |
| API como centro do sistema | [0010](adr/0010-api-como-centro.md) | RP-07 |
| JWT com usuário único | [0011](adr/0011-jwt-usuario-unico.md) | RF-25 a RF-28, RNF-C06 |
| **Gravação em disco antes da API** | [0012](adr/0012-gravacao-em-disco-antes-da-api.md) | **RNF-R01, RNF-R02** |
| Mermaid para todos os diagramas | [0013](adr/0013-mermaid-para-diagramas.md) | — (decisão de documentação) |
| Worker de transcrição em container com GPU | [0014](adr/0014-worker-em-container-com-gpu.md) | RNF-C03, RNF-P01, RNF-P04 |

---

## 6. Lacunas conhecidas

Honestidade sobre o que a matriz **não** garante:

| Lacuna | Situação |
|---|---|
| RNF-P04 (máquina utilizável durante a gravação) não tem caso de teste automatizável | Verificação manual. Automatizar exigiria medir carga do sistema de forma reprodutível, o que não se paga aqui |
| RNF-S03 (log suficiente) é subjetivo | Verificado por revisão. O critério prático: diagnosticar uma falha de campo sem reproduzi-la |
| RNF-C01 (nada sai da máquina) depende de configuração | O caminho padrão é local, mas o usuário pode configurar provedor remoto de LLM. A verificação é do caminho padrão |
| Fases 8 e 9 (desktop e front remoto) não têm requisitos próprios | São interfaces sobre requisitos existentes. Terão especificação própria quando chegarem |

---

## 7. Resumo da cobertura

| Eixo | Total | Coberto |
|---|---|---|
| Recursos de produto | 8 | 8 |
| Requisitos funcionais | 30 | 30 |
| Requisitos não-funcionais | 22 | 20 verificáveis + 2 por revisão |
| Casos de uso | 11 | 11 |
| Fluxos de exceção | 20 | 20 |
| Decisões técnicas | 14 | 14 |
