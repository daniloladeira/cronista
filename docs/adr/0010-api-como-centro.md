# ADR-0010 · API como centro do sistema

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** RP-07
- **Restringido por:** [ADR-0012](0012-gravacao-em-disco-antes-da-api.md)

## Contexto

O desenho inicial era um pacote Python puro, com linha de comando e interface desktop chamando funções diretamente. A API entraria só no fim, como camada fina de leitura para acesso remoto.

O usuário decidiu inverter: **FastAPI no centro**, com linha de comando e desktop como clientes HTTP. A motivação declarada foi acesso a partir de outra máquina, e a arquitetura cliente/servidor é a forma convencional de obtê-lo.

## Decisão

A API é a dona do estado. Registro de reuniões, transcrições, resumos, consulta e busca passam por ela. Linha de comando e interface desktop são clientes HTTP, sem acesso direto ao banco.

Exceção única, registrada em ADR próprio: **a captura de áudio não depende da API**.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Núcleo local + API só de leitura | Menos código e sem rede no caminho comum, mas duas formas de acessar o mesmo estado |
| Acesso remoto direto ao banco | Exporia o banco na rede e espalharia regra de negócio pelos clientes |

## Consequências

**Positivas.** Um único caminho para o estado, sem divergência entre interfaces. A interface desktop e a leitura remota consomem o mesmo contrato, já pronto. Autenticação num lugar só. O esquema publicado pelo FastAPI documenta a API sem risco de divergir do código.

**Negativas.** A Fase 1 vira infraestrutura pura, sem funcionalidade visível — o custo é pago antes de qualquer valor aparecer. Mais código: esquemas de requisição e resposta, cliente HTTP, tratamento de erro de rede. Rede no caminho de operações que rodam na mesma máquina. E, sem a exceção do ADR-0012, tornaria a gravação refém de um serviço.

## Gatilho de reversão

Se o custo de manter a camada HTTP para operações locais se mostrar desproporcional — sintoma típico: toda funcionalidade nova exigindo tocar em três lugares para expor o que já existe no domínio. Nesse caso, a linha de comando poderia voltar a chamar `core` diretamente, mantendo a API apenas para acesso remoto.

Como `core` permanece um pacote independente que não importa `api` ([07-arquitetura.md](../07-arquitetura.md) §2.2), essa reversão continua possível.
