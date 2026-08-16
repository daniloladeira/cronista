# Documento de Visão

> **Status:** aprovado · **Versão:** 1.0 · **Última atualização:** 2026-08-12
> Projeto ainda sem nome definitivo. Ver [16-nome.md](16-nome.md).

## 1. Introdução

### 1.1 Objetivo

Este documento define a visão do produto: qual problema ele resolve, para quem, e quais recursos de alto nível o compõem. Ele é a fonte de onde derivam os requisitos ([03-requisitos.md](03-requisitos.md)) e os casos de uso ([04-modelo-de-casos-de-uso.md](04-modelo-de-casos-de-uso.md)).

Decisões técnicas **não** pertencem a este documento. Elas estão nos ADRs ([adr/](adr/)).

### 1.2 Escopo

Um sistema pessoal que grava reuniões realizadas no computador, transcreve o áudio localmente e gera resumos estruturados — sem enviar áudio para serviços de terceiros e sem limite de uso.

## 2. Posicionamento

### 2.1 Descrição do problema

| | |
|---|---|
| **O problema de** | depender de ferramentas de transcrição que limitam o uso ou cobram mensalidade |
| **afeta** | um profissional que participa de reuniões recorrentes e precisa de registro confiável do que foi decidido |
| **cujo impacto é** | perder decisões e pendências combinadas em reunião, ou pagar recorrência por um recurso que a própria máquina tem capacidade de executar |
| **uma boa solução seria** | gravar e transcrever localmente, sem cota, com resumo de qualidade em português |

O gatilho concreto: o Notion AI, usado até então, tem limite de uso e o limite foi atingido. As alternativas de mercado caem em dois grupos — as que cobram mensalidade (Fathom Premium, ~US$20/mês) e as que oferecem plano gratuito com o recurso principal capado. Todas, sem exceção, enviam o áudio da reunião para a nuvem do fornecedor.

### 2.2 Sentença de posição do produto

> **Para** um profissional que participa de reuniões em português e precisa de registro do que foi decidido,
> **que** não quer pagar mensalidade nem esbarrar em cota de uso,
> **o produto** é uma ferramenta de gravação, transcrição e resumo de reuniões
> **que** roda inteiramente na máquina do usuário, sem limite e sem enviar áudio para terceiros.
> **Diferente de** Notion AI, Fathom, Otter e Granola,
> **o produto** não impõe cota, não exige assinatura, mantém o áudio local e é otimizado para português brasileiro com vocabulário de domínio.

### 2.3 Alternativas consideradas

A decisão de construir foi tomada com conhecimento do que já existe. Este registro evita que a pergunta "por que não usar o pronto?" precise ser refeita.

| Alternativa | Por que não substitui |
|---|---|
| Notion AI | Limite de uso — o gatilho original do projeto |
| Fathom (grátis) | Gravação ilimitada, mas recurso de resumo capado; áudio na nuvem |
| Fathom Premium | ~US$20/mês recorrente |
| Granola | Somente macOS |
| Meetily, Hyprnote | Open-source, locais, resolvem quase tudo. **Não foram descartados por deficiência técnica** — o usuário optou por construir. A diferenciação buscada é qualidade em pt-BR com vocabulário de domínio |

## 3. Stakeholders e usuários

Sistema de usuário único. Não há papéis distintos, e essa é uma decisão consciente registrada em [adr/0011-jwt-usuario-unico.md](adr/0011-jwt-usuario-unico.md).

| Stakeholder | Papel | Interesse |
|---|---|---|
| Usuário-proprietário | Único usuário, operador e desenvolvedor | Registro confiável das reuniões; custo zero; controle do próprio dado |

**Ambiente do usuário:** Windows 11, reuniões em português brasileiro pelo navegador ou por aplicativo desktop, vocabulário de domínio da área de saúde. Máquina com GPU dedicada capaz de executar transcrição local.

## 4. Visão geral do produto

### 4.1 Perspectiva

O sistema opera sozinho. Não depende de integração com plataforma de reunião — não entra na chamada, não usa API do Google Meet, Zoom ou Teams, e por isso funciona com qualquer uma delas, inclusive as que não têm API.

Depende de três recursos da máquina do usuário: dispositivo de áudio com captura de loopback, GPU para transcrição e um provedor de modelo de linguagem para o resumo.

### 4.2 Suposições e dependências

- O sistema operacional expõe o áudio de saída para captura (loopback). Verificado nesta máquina.
- A GPU tem memória suficiente para o modelo de transcrição escolhido.
- Há um provedor de LLM disponível — local por padrão.
- O usuário aceita gravar a reunião. **Consentimento dos demais participantes é responsabilidade do usuário**, não do sistema; ver seção 6.

## 5. Recursos do produto

Recursos de alto nível. O detalhamento vira requisito em [03-requisitos.md](03-requisitos.md) e comportamento em [05-detalhamento-casos-de-uso.md](05-detalhamento-casos-de-uso.md).

| ID | Recurso | Descrição |
|---|---|---|
| **RP-01** | Gravação sem bot | Captura o áudio da reunião direto da máquina, sem participante extra visível na chamada |
| **RP-02** | Separação de quem falou | Grava microfone e saída do sistema em trilhas distintas, distinguindo o usuário dos demais participantes sem depender de diarização |
| **RP-03** | Transcrição local | Converte áudio em texto na própria máquina, com marcação de tempo, sem enviar dados para fora |
| **RP-04** | Resumo estruturado | Gera pauta, decisões, pendências com responsável e pontos em aberto, em português |
| **RP-05** | Importação de áudio | Aceita arquivo de áudio ou vídeo já existente como fonte, além da gravação ao vivo |
| **RP-06** | Consulta e busca | Recupera transcrição e resumo de reuniões passadas e busca por conteúdo, com tratamento adequado de português |
| **RP-07** | Acesso autenticado | Expõe o acervo por interface autenticada, permitindo consulta a partir de outra máquina |
| **RP-08** | Retenção configurável | Aplica política de retenção ao áudio, que é o dado volumoso, preservando o texto |

### 5.1 Prioridade

| Prioridade | Recursos | Justificativa |
|---|---|---|
| Essencial | RP-01, RP-02, RP-03, RP-04 | Sem eles não há produto |
| Importante | RP-06, RP-07 | Determinam se o acervo é útil ao longo do tempo |
| Desejável | RP-05, RP-08 | Ampliam o alcance e controlam custo de disco |

## 6. Restrições

| ID | Restrição | Origem |
|---|---|---|
| RE-01 | Executa em Windows 11 | Ambiente do usuário |
| RE-02 | Transcrição roda em GPU local, sem serviço externo no caminho padrão | Privacidade e custo |
| RE-03 | Custo recorrente zero na configuração padrão | Motivação do projeto |
| RE-04 | Interface e resumos em português brasileiro | Ambiente do usuário |
| RE-05 | A API não é exposta à internet aberta | Postura de segurança — ver [10-autenticacao.md](10-autenticacao.md) |
| RE-06 | Gravar terceiros pode exigir consentimento conforme a legislação e a política da organização. O sistema **não** verifica nem obtém consentimento; a responsabilidade é do usuário | Legal |

## 7. Faixas de qualidade

Metas mensuráveis. Como medir está em [14-plano-de-testes.md](14-plano-de-testes.md).

| Atributo | Meta |
|---|---|
| Desempenho | Transcrever mais rápido que o tempo real da reunião |
| Confiabilidade | **Nenhuma reunião perdida** por indisponibilidade de API, banco ou rede |
| Precisão | WER em pt-BR igual ou melhor que a linha de base a ser medida |
| Qualidade do resumo | Igual ou superior ao Notion AI na mesma reunião, por rubrica manual |
| Usabilidade | Iniciar uma gravação em um comando |

**Sobre a meta de confiabilidade:** ela é a mais forte do documento e tem consequência de arquitetura. Áudio de reunião não se regrava — é a única falha irreversível do sistema. Isso é o que sustenta [adr/0012-gravacao-em-disco-antes-da-api.md](adr/0012-gravacao-em-disco-antes-da-api.md).

## 8. Não-objetivos

Escopo tem valor pelo que exclui. Nenhum destes é impossível; todos foram considerados e deixados de fora.

| Não-objetivo | Por quê |
|---|---|
| Multiusuário e cadastro aberto | Uso pessoal. Autenticação existe para proteger acesso remoto, não para separar usuários |
| Bot que entra na reunião | Frágil a mudança de interface das plataformas, e visível aos participantes |
| Transcrição em tempo real durante a reunião | Complexidade alta e valor baixo — o resumo é consumido depois |
| Aplicativo móvel | O áudio está no computador |
| Integração com CRM, calendário ou Slack | Escopo de produto comercial, não de ferramenta pessoal |
| Tradução entre idiomas | O uso é monolíngue |

## 9. Documentos relacionados

| Documento | Papel |
|---|---|
| [02-glossario.md](02-glossario.md) | Termos usados aqui e nos demais |
| [03-requisitos.md](03-requisitos.md) | Recursos desta seção 5 detalhados em RF e RNF |
| [04-modelo-de-casos-de-uso.md](04-modelo-de-casos-de-uso.md) | Atores e casos de uso |
| [06-matriz-rastreabilidade.md](06-matriz-rastreabilidade.md) | Prova de que recurso → requisito → caso de uso → teste fecha |
| [15-roadmap.md](15-roadmap.md) | Ordem de construção |
| [adr/](adr/) | Decisões técnicas e seus porquês |
