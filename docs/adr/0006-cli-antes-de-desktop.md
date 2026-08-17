# ADR-0006 · Linha de comando antes da interface desktop

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** RNF-U01

## Contexto

O destino do projeto é uma aplicação desktop com ícone na bandeja: é assim que uma ferramenta de gravação de reunião se usa no dia a dia. A pergunta era se valia começar por ela.

Gravar exige captura local, transcrever exige GPU local, e resumir exige um provedor de modelo. Nada disso é resolvido pela interface: a interface só aciona. Construí-la primeiro significaria depurar simultaneamente captura de áudio, laço de eventos gráfico e comunicação com a API.

## Decisão

Construir primeiro a **linha de comando** e adiar a interface desktop para a Fase 8, sobre a mesma API.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Desktop desde o início | Depurar áudio dentro de laço gráfico multiplica a dificuldade de cada problema |
| Somente linha de comando, sem desktop | Iniciar uma gravação pelo terminal antes de cada reunião cansa; a interface se paga no uso diário |

## Consequências

**Positivas.** Cada problema é depurado isoladamente. A linha de comando vira contrato executável para a interface desktop: tudo que ela faz, a interface fará chamando os mesmos endpoints. Entrega valor utilizável desde a Fase 2. Automatizável em teste, ao contrário de interface gráfica.

**Negativas.** O sistema fica desconfortável de usar até a Fase 8, e é justamente o conforto que determina se uma ferramenta de reunião é usada de fato. Há risco de o projeto parar na Fase 5 ou 6 e nunca ganhar a interface que o tornaria hábito.

## Gatilho de reversão

Se o desconforto da linha de comando fizer o usuário deixar de gravar reuniões, a Fase 8 deve ser antecipada, mesmo que fases funcionais fiquem para depois. Uma ferramenta que não se usa não tem valor, por mais completa que esteja.
