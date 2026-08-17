"""Testa captura de loopback em CADA dispositivo de saida, nao so o padrao.

Existe porque o dispositivo de saida padrao pode mudar (ex.: Bluetooth
conectado) e alguns nao suportam loopback WASAPI direito, especialmente
headsets Bluetooth dependendo do driver/perfil.

    python scripts/diagnose_loopback.py

Deixe algo tocando durante a execucao inteira.
"""

from __future__ import annotations

import sys

import numpy as np
import soundcard as sc

DURATION_SECONDS = 2
SAMPLE_RATE = 16_000


def main() -> int:
    default = sc.default_speaker()
    speakers = sc.all_speakers()

    print(f"Saida padrao atual: {default.name}\n")
    print(f"Testando loopback em {len(speakers)} dispositivo(s) de saida.")
    print("Deixe algo tocando durante todo o teste.\n")

    results: list[tuple[str, bool, float, str | None]] = []

    for speaker in speakers:
        marker = " (padrao)" if speaker.name == default.name else ""
        print(f"  {speaker.name}{marker} ...", end=" ", flush=True)
        try:
            loopback = sc.get_microphone(speaker.name, include_loopback=True)
            with loopback.recorder(samplerate=SAMPLE_RATE, channels=1) as rec:
                data = rec.record(numframes=SAMPLE_RATE * DURATION_SECONDS)
            peak = float(np.abs(data).max())
            ok = peak > 0.01
            print(f"pico={peak:.4f} {'OK' if ok else 'SEM SINAL'}")
            results.append((speaker.name, ok, peak, None))
        except Exception as exc:  # noqa: BLE001
            print(f"ERRO: {exc}")
            results.append((speaker.name, False, 0.0, str(exc)))

    print("\nResumo:")
    for name, ok, peak, error in results:
        status = "ERRO" if error else ("OK" if ok else "SEM SINAL")
        print(f"  {status:10} pico={peak:.4f}  {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
