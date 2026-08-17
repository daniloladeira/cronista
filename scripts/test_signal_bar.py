"""Verificacao manual do medidor de sinal real (Rich), com captura de audio
de verdade -- traco horizontal com historico, nao mais escada vertical.

    python scripts/test_signal_bar.py

Grava 8 segundos. Fale e deixe algo tocando.
"""

from __future__ import annotations

import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cronista.client import capture, signal_bar

DURATION_SECONDS = 8


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cronista_test_bar_") as tmp:
        output_dir = Path(tmp)
        stop_event = threading.Event()

        def stop_after_a_while() -> None:
            time.sleep(DURATION_SECONDS)
            stop_event.set()

        threading.Thread(target=stop_after_a_while, daemon=True).start()

        with signal_bar.SignalBar() as bar:
            result = capture.record(output_dir, stop_event=stop_event, on_level=bar.update)

        print("\nResultado:")
        for track in result.tracks:
            sinal = "com sinal" if track.had_signal else "SEM SINAL"
            print(f"  {track.speaker:>7} | {sinal:10} | {track.duration_ms}ms")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
