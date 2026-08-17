"""Geração de UUIDv7. Ver docs/adr/0004 e docs/adr/0008.

Python 3.14 traz uuid7() na biblioteca padrão; o projeto roda em 3.13
(ADR-0008), daí esta implementação própria conforme RFC 9562.
"""

from __future__ import annotations

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    unix_ts_ms = int(time.time() * 1000)
    ts_bytes = unix_ts_ms.to_bytes(6, "big")
    rand_bytes = os.urandom(10)

    b = bytearray(ts_bytes + rand_bytes)
    b[6] = (b[6] & 0x0F) | 0x70  # versão 7
    b[8] = (b[8] & 0x3F) | 0x80  # variante RFC 4122

    return uuid.UUID(bytes=bytes(b))
