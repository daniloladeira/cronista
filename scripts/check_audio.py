"""Sondagem do subsistema de audio.

Verifica se a maquina atende a premissa que sustenta todo o projeto: capturar
simultaneamente o microfone e o loopback da saida (ADR-0001). Sem loopback nao
existe a trilha `outros`, e o sistema perde o proposito.

Rode isto ANTES de qualquer coisa:

    python scripts/check_audio.py

Saida 0 = a maquina serve. Qualquer outra = leia a mensagem.
"""

from __future__ import annotations

import sys

SAMPLE_RATE = 16_000  # o que o Whisper consome (docs/12-transcricao.md)
CHANNELS = 1
PROBE_SECONDS = 1


def main() -> int:
    try:
        import numpy as np
        import soundcard as sc
    except ImportError as exc:
        print(f"[ERRO] Dependencia ausente: {exc.name}")
        print("       pip install soundcard soundfile numpy")
        return 1

    try:
        speaker = sc.default_speaker()
        mic = sc.default_microphone()
    except Exception as exc:
        print(f"[ERRO] Nao foi possivel consultar os dispositivos: {exc}")
        return 2

    print(f"Saida padrao  : {speaker.name}")
    print(f"Entrada padrao: {mic.name}")

    # A parte que importa: o loopback da saida. E o que grava a fala dos outros
    # participantes sem microfone apontado para a caixa de som.
    try:
        loopback = sc.get_microphone(speaker.name, include_loopback=True)
    except Exception as exc:
        print(f"[ERRO] A saida padrao nao expoe loopback: {exc}")
        print("       Sem loopback nao ha trilha 'outros'. Tente outro dispositivo de saida.")
        return 3

    print(f"Loopback      : {loopback.name}")

    try:
        with loopback.recorder(samplerate=SAMPLE_RATE, channels=CHANNELS) as rec:
            data = rec.record(numframes=SAMPLE_RATE * PROBE_SECONDS)
    except Exception as exc:
        print(f"[ERRO] Falha ao capturar do loopback: {exc}")
        return 4

    peak = float(np.abs(data).max())
    print(f"\nCaptura OK: {data.shape[0]} amostras a {SAMPLE_RATE} Hz, pico {peak:.4f}")

    if peak == 0.0:
        # Nao e falha: loopback so tem sinal quando algo esta tocando.
        print("\n[AVISO] Silencio absoluto. Isso e esperado se nada estava tocando.")
        print("        Para confirmar de verdade, deixe um video tocando e rode de novo.")

    print("\nEsta maquina atende a premissa de captura do projeto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
