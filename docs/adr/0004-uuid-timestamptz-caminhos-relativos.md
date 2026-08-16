# ADR-0004 · UUIDv7, timestamptz e caminhos relativos

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** RF-07

## Contexto

Três escolhas de modelagem que custam praticamente nada no início e viram migração dolorosa depois que existem dados reais. Foram decididas juntas porque compartilham a mesma natureza: são baratas agora e caras depois.

O contexto que as tornou necessárias: o cliente pode gravar com a API fora do ar e registrar depois, e o usuário manifestou intenção de acessar o acervo de outra máquina.

## Decisão

1. **Identificadores `uuid` versão 7**, gerados na aplicação, em vez de inteiro sequencial.
2. **`timestamptz` sempre em UTC**, com conversão para hora local apenas na apresentação.
3. **Caminhos de áudio relativos** a uma raiz configurável, com coluna `host` registrando a máquina de origem.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Inteiro sequencial | Duas máquinas gravando offline geram `1, 2, 3` cada uma. Ao consolidar, colidem |
| UUIDv4 | Resolve colisão, mas é aleatório: destrói localidade no índice |
| Timestamp local ou texto ISO sem fuso | Fonte clássica de defeito, agravada por horário de verão |
| Caminho absoluto | `C:\Users\...` não resolve em outra máquina, nem se o acervo mudar de disco |

## Consequências

**Positivas.** Registro offline nunca colide. UUIDv7 preserva ordenação temporal, mantendo o índice eficiente. Mover o acervo inteiro para outro disco não exige tocar em nenhuma linha do banco — o que também torna a renomeação do projeto barata ([16-nome.md](../16-nome.md)). Ambiguidade de fuso eliminada na origem.

**Negativas.** UUID ocupa mais espaço que inteiro e é menos legível ao depurar manualmente. UUIDv7 é gerado na aplicação, não pelo banco. Caminhos relativos exigem resolver a raiz em toda leitura de arquivo — dois níveis de indireção que precisam estar corretos.

## Gatilho de reversão

Nenhum previsto. São decisões cujo custo é permanente e baixo, e cujo benefício aparece exatamente no cenário que o projeto já planeja ter. Reverter só faria sentido se o acervo fosse garantidamente de máquina única e nunca migrado — condição que já se sabe falsa.
