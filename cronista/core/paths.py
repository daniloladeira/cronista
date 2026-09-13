"""Constantes de caminho compartilhadas entre client/, worker/ e api/, sem
depender de pydantic_settings (ver cronista/client/settings.py)."""

from __future__ import annotations

# DATA_ROOT/RECORDINGS_DIRNAME/<audio_dir>/<falante>.wav (docs/08 §2).
# pending.json fica direto em DATA_ROOT, não dentro daqui.
RECORDINGS_DIRNAME = "recordings"
