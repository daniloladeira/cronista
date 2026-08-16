# ADR-0012 · Gravação em disco antes de qualquer chamada à API

- **Status:** aceito
- **Data:** 2026-08-12
- **Requisitos relacionados:** RNF-R01, RNF-R02
- **Restringe:** [ADR-0010](0010-api-como-centro.md)

## Contexto

O [ADR-0010](0010-api-como-centro.md) colocou a API no centro: todo estado passa por ela. Aplicada sem exceção, essa regra levaria o cliente de captura a enviar áudio à API, que persistiria e conduziria o resto.

Isso cria um problema que nenhuma outra parte do sistema tem. **Áudio de reunião não se regrava.** Se o container do banco estiver parado, se a API não subiu, se houve um erro de configuração — a reunião acontece uma vez e acabou. É a única falha irreversível do sistema inteiro.

Todas as demais operações são repetíveis: transcrição refaz, resumo gera de novo, busca consulta outra vez. Gravação, não.

Agrava o quadro que cliente e API rodam na **mesma máquina**. Fazer a captura depender de um serviço local, atravessando rede para chegar a um processo vizinho, adiciona um modo de falha sem trazer benefício algum.

## Decisão

A captura **escreve os arquivos de áudio em disco local antes de qualquer chamada de rede**, e nunca depende da API para iniciar ou continuar uma gravação.

O registro na API é passo posterior e reconciliável. Falhando, a reunião fica marcada localmente como pendente e o comando **encerra com sucesso** — porque o que importava foi preservado.

A recuperação é UC-11, que existe exclusivamente por causa desta decisão.

## Consequências

**Positivas.** Nenhuma reunião se perde por indisponibilidade de API, banco ou rede (RNF-R01). Gravar funciona com tudo mais desligado. O usuário não precisa lembrar de subir o container antes de uma reunião — que é exatamente o momento em que ninguém lembra.

**Negativas.** Duas fontes de verdade transitórias: o índice local de pendências e o banco. O cliente precisa de estado próprio em disco. Uma reunião pode existir localmente e não no acervo por um período. Complexidade adicional de reconciliação, incluindo o caso de envio parcial de trilhas.

## Gatilho de reversão

**Nenhum.** Este ADR existe para proteger a única operação irreversível do sistema. Enquanto a captura acontecer na máquina do usuário, a decisão vale.

Só deixaria de fazer sentido se a captura passasse a ocorrer em ambiente onde a persistência fosse garantida por outro meio — cenário que não está no roadmap e contraria o documento de visão.

## Verificação

Esta é a decisão com o teste mais importante do projeto: **CT-08** derruba a API no meio de uma gravação e confirma que o áudio sobrevive íntegro, que a pendência é registrada e que a reconciliação posterior completa o registro. Ver [14-plano-de-testes.md](../14-plano-de-testes.md) §3.2.
