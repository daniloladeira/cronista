# ADR-0011 · JWT com usuário único

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** RF-25 a RF-28, RNF-C06

## Contexto

Com a API no centro ([ADR-0010](0010-api-como-centro.md)) e a intenção de acessá-la de outra máquina, um serviço sem autenticação seria um serviço aberto.

A pergunta seguinte era o alcance: proteger o acesso de uma pessoa, ou preparar o terreno para várias. O usuário foi explícito — **só ele**, e o acesso remoto é de leitura.

Isso importa porque a diferença é grande. Multiusuário exige tabela de usuários, coluna de propriedade em cada reunião, filtro em toda consulta e cadastro. Usuário único não exige nada disso.

## Decisão

Autenticação por usuário e senha com JWT, para **um único usuário**. Credencial em variável de ambiente, com hash Argon2. **Sem tabela de usuários e sem coluna de propriedade nas reuniões.**

A API não é exposta à internet aberta: rede privada ou local.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Chave de API única no cabeçalho | Mais simples, mas sem expiração nem renovação; um vazamento é permanente |
| OAuth com provedor externo | Dependência externa e complexidade sem contrapartida para um usuário |
| Tabela de usuários com uma linha | Custo de multiusuário sem o benefício, e adia a decisão em vez de tomá-la |

## Consequências

**Positivas.** Implementação pequena e fácil de acertar. Sem tela de cadastro, sem recuperação de senha, sem verificação de e-mail. Nenhuma consulta precisa filtrar por dono. Token expira, ao contrário de chave fixa.

**Negativas.** Uma segunda pessoa não pode usar o sistema sem migração. Não há revogação de token individual — invalidar tudo exige trocar o segredo. Recuperar senha é editar um arquivo. A postura de segurança **depende** de a API não estar exposta publicamente: se isso mudar, faltam limite de tentativas, HTTPS obrigatório e auditoria.

## Gatilho de reversão

**No dia em que uma segunda pessoa precisar usar o sistema.** A migração é conhecida e mecânica, e está registrada aqui para não precisar ser redescoberta:

1. Criar tabela de usuários e migrar a credencial do arquivo de ambiente.
2. Acrescentar coluna de proprietário em `meetings`, com preenchimento retroativo de um único valor.
3. Filtrar por proprietário em toda consulta.
4. Acrescentar cadastro e recuperação de senha.

Gatilho independente: **se a API for exposta à internet aberta**, este ADR e [10-autenticacao.md](../10-autenticacao.md) precisam ser revistos por inteiro, mesmo continuando com um só usuário.
