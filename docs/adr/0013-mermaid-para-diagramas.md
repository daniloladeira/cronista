# ADR-0013 · Mermaid para todos os diagramas

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** n/d (decisão de documentação)

## Contexto

A documentação inclui diagramas UML. Duas ferramentas baseadas em texto foram consideradas: Mermaid e PlantUML.

PlantUML tem notação UML estrita, incluindo diagrama de casos de uso com ator em boneco e caso de uso em elipse, que o Mermaid não possui. Em compensação, exige Java e Graphviz para renderizar, e não é exibido automaticamente no GitHub: o arquivo-fonte aparece como bloco de texto, a menos que a imagem renderizada seja gerada e versionada junto.

Chegou-se a planejar uma divisão: PlantUML nos quatro diagramas em que o Mermaid é fraco, Mermaid no resto. O usuário recusou a dependência de Java.

**O repositório também serve de portfólio.** Isso muda o critério decisivo: diagrama que não aparece para quem abre o repositório não cumpre sua função, por mais correta que seja sua notação.

## Decisão

Usar **Mermaid em todos os diagramas**, embutidos nos próprios documentos. Sem renderização, sem imagens versionadas, sem etapa de compilação.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| PlantUML em tudo | Exige Java e Graphviz; não renderiza no GitHub sem imagem versionada |
| Mermaid + PlantUML | Melhor notação, mas duas ferramentas e um toolchain para manter |
| Servidor público do PlantUML | Dispensa Java, mas envia o fonte dos diagramas a um terceiro |
| Ferramenta gráfica | Diagrama binário não versiona em diff legível |

## Consequências

**Positivas.** Todos os diagramas aparecem no GitHub e no editor sem nada instalado. Fonte em texto, com diff legível. Nenhuma etapa de compilação para esquecer de rodar: não há como o diagrama exibido divergir do fonte. Nada é enviado a terceiros.

**Negativas.** O **diagrama de casos de uso deixa de ser notação UML estrita**: sem ator em boneco e sem elipse, ele é desenhado como fluxograma com atores em retângulos e casos de uso em formas arredondadas dentro da fronteira do sistema. A aproximação é declarada no próprio documento ([04-modelo-de-casos-de-uso.md](../04-modelo-de-casos-de-uso.md) §3).

O **diagrama de comunicação foi removido** do conjunto: ele carrega a mesma informação do diagrama de sequência, mudando apenas a ênfase de layout, e reproduzi-lo em Mermaid geraria redundância sem ganho.

## Gatilho de reversão

Se estes artefatos precisarem ser submetidos a avaliação que exija notação UML formal, uma disciplina acadêmica, por exemplo. Nesse caso, o diagrama de casos de uso é refeito em PlantUML e a imagem renderizada é versionada. É **um** diagrama, não o conjunto.
