"""Ponte pro cronista-tui: reaproveita cronista.client.capture (soundcard)
pra devolver dispositivos reais em JSON."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cronista.client import capture

print(
    json.dumps(
        {
            "entrada": [{"name": d.name, "is_default": d.is_default} for d in capture.list_input_devices()],
            "saida": [{"name": d.name, "is_default": d.is_default} for d in capture.list_output_devices()],
        }
    )
)
