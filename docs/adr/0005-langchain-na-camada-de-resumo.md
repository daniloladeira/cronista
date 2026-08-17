# ADR-0005 · LangChain na camada de resumo

- **Status:** aceito. **Contra recomendação técnica, por decisão deliberada**
- **Data:** 2026-08-12
- **Requisitos relacionados:** RF-18, RNF-S04

## Contexto

A camada de resumo faz uma coisa: pega a transcrição, preenche um template de prompt, chama um modelo e recebe markdown de volta. Uma chamada. Sem agente, sem ferramentas, sem roteamento, sem recuperação de documentos.

Surgiu a pergunta de usar LangChain. A recomendação técnica foi **contra**, com três razões:

1. O framework existe para orquestrar cadeias complexas; aqui há uma chamada única, que em código direto ocupa algumas dezenas de linhas.
2. Árvore de dependências pesada, com risco concreto de conflito de versão com `ctranslate2` no mesmo ambiente.
3. Churn de API conhecido entre versões, num projeto pessoal a que se volta depois de meses.

O que o framework de fato entrega neste caso é a troca de provedor com interface única, o que um `Protocol` de trinta linhas também entregaria.

**O usuário decidiu adotar LangChain mesmo assim**, com a razão explícita de aprender o framework. A camada de resumo é o ponto de menor risco do sistema para isso: não é o caminho irreversível, não é o gargalo de desempenho, e está isolada atrás de uma fronteira clara.

## Decisão

Usar **LangChain** na camada de resumo, com as integrações de Ollama e do provedor remoto.

## Consequências

**Positivas.** Troca de provedor por configuração. Estratégias prontas para transcrição maior que a janela de contexto. Aprendizado de um framework difundido, em contexto real e de baixo risco.

**Negativas.** Dependências substancialmente maiores do que a tarefa exige. Risco de conflito com `ctranslate2`, já previsto e mitigado pela arquitetura de processos separados ([07-arquitetura.md](../07-arquitetura.md) §7). Abstração entre o código e a API do modelo, que atrapalha exatamente quando o resumo em português sair ruim e for preciso entender por quê. Exposição a quebras de API entre versões.

## Gatilho de reversão

Qualquer um destes basta:

- Conflito de dependência que não se resolva nem com ambiente separado para o worker.
- Uma atualização quebrar a camada e o conserto custar mais que reescrevê-la sem o framework.
- Ficar difícil diagnosticar má qualidade de resumo por causa da camada de abstração.

**A reversão é barata e isso é intencional:** a camada é um arquivo atrás de uma interface. Substituí-la por chamadas diretas ao SDK de cada provedor é trabalho de uma sessão, e nada fora dela precisa mudar (RNF-S04).
