"""Mede WER entre uma transcrição de referência (feita à mão) e a saída do
Whisper, para CT-36 (docs/14-plano-de-testes.md §4).

Uso:
    python scripts/measure_wer.py <referencia.txt> <hipotese.txt>

Os dois arquivos aceitam linha corrida OU uma linha por segmento no formato
"falante: texto" (é o que os scripts de export do CT-36 geram, pra facilitar
conferência contra o áudio) — o prefixo "falante: " é removido antes de
comparar, porque WER mede acerto de palavra, não atribuição de falante
(isso já é CT-17). Normalização (minúsculas, remove pontuação, espaços
redundantes) é aplicada nos dois lados antes de comparar, para não punir
diferença só de formatação.
"""

from __future__ import annotations

import re
import sys

import jiwer

_PREFIXO_FALANTE = re.compile(r"^\w+:\s*")


def _le_texto(caminho: str) -> str:
    linhas = open(caminho, encoding="utf-8").read().splitlines()
    return " ".join(_PREFIXO_FALANTE.sub("", linha) for linha in linhas)

_TRANSFORM = jiwer.Compose(
    [
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.Strip(),
        jiwer.ReduceToListOfListOfWords(),
    ]
)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # console do Windows põe mojibake em acento sem isso
    if len(sys.argv) != 3:
        print(f"Uso: python {sys.argv[0]} <referencia.txt> <hipotese.txt>", file=sys.stderr)
        raise SystemExit(1)

    referencia_path, hipotese_path = sys.argv[1], sys.argv[2]
    referencia = _le_texto(referencia_path)
    hipotese = _le_texto(hipotese_path)

    resultado = jiwer.process_words(
        referencia,
        hipotese,
        reference_transform=_TRANSFORM,
        hypothesis_transform=_TRANSFORM,
    )

    total_palavras = resultado.hits + resultado.substitutions + resultado.deletions
    print(f"WER: {resultado.wer:.1%}")
    print(f"Palavras na referência: {total_palavras}")
    print(f"Acertos: {resultado.hits}")
    print(f"Substituições: {resultado.substitutions}")
    print(f"Remoções (Whisper deixou de fora): {resultado.deletions}")
    print(f"Inserções (Whisper inventou): {resultado.insertions}")


if __name__ == "__main__":
    main()
