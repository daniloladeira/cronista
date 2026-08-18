"""Matemática do brilho que varre uma barra de progresso, portada do
projeto torlink (`src/ui/sheen.ts`, `baairon/torlink`) — sem consumidor
ainda. Registrado aqui pra quando a barra de progresso da transcrição
existir (docs/17-identidade-visual-cli.md §3: "Ainda não implementado;
registrado aqui para não ser esquecido quando a Fase 3 chegar").

O brilho é um sino de cosseno que varre as células preenchidas. A posição
avança uma fração de SHEEN_SPEED a cada quadro, então o pico desliza entre
células (intensidade interpolada) em vez de pular uma célula inteira por
vez — mas as células continuam discretas (pixelizadas), mesmo padrão do
medidor de sinal (docs/17 §6).
"""

from __future__ import annotations

import math

SHEEN_PEAK = "#FFFFFF"  # branco, mesmo tom do brilho do banner (§7)
SHEEN_RADIUS = 4.5  # meia-largura do sino, em células
SHEEN_GAP = 8  # células apagadas entre uma varredura e a próxima
SHEEN_TICK_MS = 40  # intervalo de quadro (~25fps)
SHEEN_SPEED = 0.45  # células avançadas por quadro (~11 células/s)
SHEEN_MAX = 0.9  # mistura máxima em direção a SHEEN_PEAK, no pico


def sheen_period(width: int) -> float:
    """Duração total de um ciclo de varredura, em células, pra uma barra
    de `width` células."""
    return math.ceil(width + SHEEN_RADIUS * 2) + SHEEN_GAP


def sheen_center(tick: int, period: float) -> float:
    """Centro fracionário do sino num quadro dado (repete a cada `period`)."""
    return ((tick * SHEEN_SPEED) % period) - SHEEN_RADIUS


def sheen_intensity(i: int, center: float) -> float:
    """Intensidade do brilho (0..SHEEN_MAX) na célula `i`, dado o centro
    atual do sino."""
    d = abs(i - center)
    if d >= SHEEN_RADIUS:
        return 0.0
    return 0.5 * (1 + math.cos(math.pi * d / SHEEN_RADIUS)) * SHEEN_MAX


def sheen_loop_ticks(period: float) -> int:
    """Quadros num ciclo visual completo."""
    return round(period / SHEEN_SPEED)
