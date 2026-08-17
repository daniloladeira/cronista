"""Verificacao manual de cronista/client/capture.py, antes de integrar na CLI.

Grava 6 segundos em duas trilhas, num diretorio temporario, e imprime o
resultado. Fale ao microfone e deixe algo tocando na saida durante a
gravacao, para confirmar sinal nas duas trilhas.

    python scripts/test_capture.py

Depois, TOQUE OS DOIS ARQUIVOS E CONFIRME: voce.wav tem a sua voz,
outros.wav tem o audio do sistema. Trilha trocada e o defeito mais
perigoso que existe aqui, porque corrompe todo resumo gerado depois
(docs/14-plano-de-testes.md secao 6, passo 4).
"""

from __future__ import annotations

import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cronista.client import capture

DURATION_SECONDS = 6


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cronista_test_capture_") as tmp:
        output_dir = Path(tmp)
        stop_event = threading.Event()

        def stop_after_a_while() -> None:
            time.sleep(DURATION_SECONDS)
            stop_event.set()

        # As duas trilhas chamam on_level ao mesmo tempo, de threads diferentes.
        # Um print() por trilha, sem trava, faz uma atropelar a outra na
        # mesma linha do terminal — por isso o estado é compartilhado e um
        # único ponto desenha, com lock. É o mesmo problema que o design em
        # docs/17-identidade-visual-cli.md evita na implementação real.
        levels = {"voce": 0.0, "outros": 0.0}
        lock = threading.Lock()

        def on_level(speaker: str, level: float) -> None:
            with lock:
                levels[speaker] = level
                bar_voce = "#" * int(levels["voce"] * 15)
                bar_outros = "#" * int(levels["outros"] * 15)
                print(
                    f"\r  voce [{bar_voce:<15}]   outros [{bar_outros:<15}]",
                    end="",
                )

        print(f"Gravando {DURATION_SECONDS}s. Fale e deixe algo tocando...\n")
        threading.Thread(target=stop_after_a_while, daemon=True).start()

        result = capture.record(output_dir, stop_event=stop_event, on_level=on_level)

        print("\n\nResultado:")
        for track in result.tracks:
            status = f"ERRO: {track.error}" if track.error else "OK"
            sinal = "com sinal" if track.had_signal else "SEM SINAL"
            print(
                f"  {track.speaker:>7} | {status:20} | {sinal:10} | "
                f"{track.duration_ms}ms | {track.size_bytes} bytes | {track.device}"
            )

        print(f"\nArquivos em: {output_dir}")
        print("Copie-os para um lugar permanente antes de sair, ou eles serao apagados.")
        input("Pressione Enter para apagar o diretorio temporario e sair...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
