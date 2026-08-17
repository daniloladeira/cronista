# API · Contrato

> **Versão:** 1.0 · **Última atualização:** 2026-08-12
> **Nível deste documento: contrato.** Define quais endpoints existem, o que recebem e o que devolvem. Esquemas campo a campo pertencem ao código, ver §6.

## 1. Convenções

- Base: `/api/v1`
- Corpo em JSON, exceto envio de áudio (`multipart/form-data`)
- Todos os endpoints exigem `Authorization: Bearer <token>`, exceto `/auth/login` e `/health` (RN-10)
- Instantes em ISO 8601, UTC
- Identificadores em UUID

## 2. Endpoints

### Autenticação

| Método | Rota | Propósito | UC |
|---|---|---|---|
| `POST` | `/auth/login` | Troca usuário e senha por par de tokens | UC-01 |
| `POST` | `/auth/refresh` | Renova o token de acesso | UC-01 |

### Reuniões

| Método | Rota | Propósito | UC |
|---|---|---|---|
| `POST` | `/meetings` | Registra uma reunião e devolve seu identificador | UC-10 |
| `POST` | `/meetings/{id}/tracks` | Envia uma trilha de áudio e associa falante | UC-10 |
| `GET` | `/meetings` | Lista reuniões com estado, com paginação | UC-07 |
| `GET` | `/meetings/{id}` | Dados de uma reunião, suas trilhas e resumos | UC-07 |
| `GET` | `/meetings/{id}/transcript` | Transcrição mesclada, com falante e instante | UC-07 |
| `PATCH` | `/meetings/{id}` | Altera título | UC-07 |
| `DELETE` | `/meetings/{id}` | Remove a reunião e tudo que dela deriva | UC-09 |

### Processamento

| Método | Rota | Propósito | UC |
|---|---|---|---|
| `POST` | `/meetings/{id}/transcribe` | Recoloca a reunião na fila de transcrição | UC-05 |
| `POST` | `/meetings/{id}/summarize` | Gera um novo resumo | UC-06 |

### Busca e saúde

| Método | Rota | Propósito | UC |
|---|---|---|---|
| `GET` | `/search` | Busca textual nos segmentos | UC-08 |
| `GET` | `/health` | Verificação de saúde. **Sem autenticação** | n/d |

**`POST /meetings/{id}/tracks` serve gravação e importação.** Os dois caminhos convergem aqui, que é o que torna UC-04 barato. A diferença está apenas no `speaker` enviado e em `source` na criação da reunião.

## 3. Formatos essenciais

Somente o que precisa estar fixado antes do código.

**Registro de reunião** (`POST /meetings`) recebe título, origem (`capture` ou `import`), máquina, instante de início, instante de término e duração. Devolve o identificador e o estado inicial.

**Envio de trilha** (`POST /meetings/{id}/tracks`) recebe o arquivo, o falante (`voce`, `outros` ou `desconhecido`), taxa de amostragem, canais e, opcionalmente, o dispositivo de origem.

**Transcrição** (`GET /meetings/{id}/transcript`) devolve a lista de segmentos já mesclada e ordenada, cada um com falante, início, fim e texto. A mesclagem é do servidor: o cliente nunca recebe trilhas separadas para juntar.

**Busca** (`GET /search`) recebe a expressão e filtros opcionais de período e falante. Devolve trechos com reunião de origem, instante, falante e texto (RF-24).

## 4. Erros

| Código | Quando | Observação |
|---|---|---|
| `400` | Corpo inválido, expressão de busca malformada | Mensagem indica o campo |
| `401` | Token ausente, inválido ou expirado | Dispara renovação automática no cliente |
| `404` | Reunião inexistente | |
| `409` | Operação incompatível com o estado atual | Ex.: resumir reunião não transcrita (RN-07) |
| `413` | Trilha excede o limite aceito | Cliente preserva o arquivo local (UC-10, FE-03) |
| `422` | Validação de esquema | |
| `503` | Dependência externa indisponível | Ex.: provedor de LLM fora do ar (UC-06, FE-01) |

**`409` e `503` carregam a maior parte do valor.** São eles que distinguem "você pediu algo fora de hora" de "algo externo falhou", a distinção que RNF-U03 exige que o usuário consiga fazer.

## 5. Comportamentos que o contrato garante

| Garantia | Origem |
|---|---|
| Registrar reunião é idempotente por identificador do cliente | UC-11 reenvia sem duplicar |
| Enviar trilha já enviada substitui, não duplica | UC-10, FA-01 |
| Gerar resumo nunca sobrescreve o anterior | RN-03 |
| Excluir reunião ausente responde sucesso | UC-09, FE-02, remoção é idempotente |
| Nenhum endpoint bloqueia esperando transcrição | O worker é assíncrono |

## 6. O que este documento deliberadamente não fixa

Nomes exatos de campo, formatos de paginação, cabeçalhos de cache e esquemas completos de resposta. Eles pertencem ao código, onde o FastAPI os gera a partir dos modelos e publica em `/docs`, documentação que não tem como divergir da implementação, ao contrário desta.

O que está aqui é o que precisa ser decidido **antes** de escrever código: quais endpoints existem, o que cada um significa e como o sistema se comporta em erro.
