"""Mescla os segmentos transcritos de várias trilhas em uma única linha do
tempo, por ordem de início (docs/12-transcricao.md §5).
"""

from __future__ import annotations

from dataclasses import dataclass

from cronista.worker.transcription import TranscribedSegment


@dataclass(frozen=True)
class MergedSegment:
    speaker: str
    start_ms: int
    end_ms: int
    text: str


def merge_tracks(segments_by_speaker: dict[str, list[TranscribedSegment]]) -> list[MergedSegment]:
    """Une os segmentos de todas as trilhas em ordem cronológica de início.

    Aceita qualquer quantidade de falantes, não só `voce`/`outros`
    (docs/12-transcricao.md §1: "uma lista de trilhas, nunca um número
    fixo"). A atribuição de falante vem da chave do dicionário — a mesma
    que já está em `Track.speaker`, decidida pela origem do sinal, nunca
    por análise de conteúdo (RN-01) — não da ordenação em si.

    Como os relógios das trilhas partem do mesmo instante de gravação, não
    há alinhamento a fazer (§5). Sobreposição de fala produz segmentos com
    intervalos que se cruzam; isso é preservado, não resolvido — a única
    transformação aqui é ordenar por início.
    """
    merged = [
        MergedSegment(speaker=speaker, start_ms=segment.start_ms, end_ms=segment.end_ms, text=segment.text)
        for speaker, segments in segments_by_speaker.items()
        for segment in segments
    ]
    merged.sort(key=lambda segment: segment.start_ms)
    return merged
