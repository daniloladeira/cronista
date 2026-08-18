"""Testes de cronista.worker.merge (docs/12-transcricao.md §5)."""

from __future__ import annotations

from cronista.worker.merge import MergedSegment, merge_tracks
from cronista.worker.transcription import TranscribedSegment


def _seg(start_ms: int, end_ms: int, text: str) -> TranscribedSegment:
    return TranscribedSegment(start_ms=start_ms, end_ms=end_ms, text=text)


def test_merge_interleaves_two_tracks_by_start() -> None:
    result = merge_tracks(
        {
            "voce": [_seg(0, 1000, "oi"), _seg(3000, 4000, "tudo bem?")],
            "outros": [_seg(1200, 2800, "oi, tudo"), _seg(4200, 5000, "sim")],
        }
    )

    assert result == [
        MergedSegment(speaker="voce", start_ms=0, end_ms=1000, text="oi"),
        MergedSegment(speaker="outros", start_ms=1200, end_ms=2800, text="oi, tudo"),
        MergedSegment(speaker="voce", start_ms=3000, end_ms=4000, text="tudo bem?"),
        MergedSegment(speaker="outros", start_ms=4200, end_ms=5000, text="sim"),
    ]


def test_merge_preserves_overlapping_segments_without_resolving() -> None:
    # Os dois falando ao mesmo tempo: os intervalos se cruzam, e isso não é
    # corrigido, só ordenado por início (docs/12 §5).
    result = merge_tracks(
        {
            "voce": [_seg(0, 3000, "deixa eu falar")],
            "outros": [_seg(1000, 2000, "só um segundo")],
        }
    )

    assert result == [
        MergedSegment(speaker="voce", start_ms=0, end_ms=3000, text="deixa eu falar"),
        MergedSegment(speaker="outros", start_ms=1000, end_ms=2000, text="só um segundo"),
    ]


def test_merge_single_track_passthrough() -> None:
    # Importação entrega uma trilha só (docs/12 §1) — a assinatura não é
    # amarrada a exatamente duas.
    result = merge_tracks({"voce": [_seg(0, 1000, "a"), _seg(1000, 2000, "b")]})

    assert result == [
        MergedSegment(speaker="voce", start_ms=0, end_ms=1000, text="a"),
        MergedSegment(speaker="voce", start_ms=1000, end_ms=2000, text="b"),
    ]


def test_merge_empty_tracks_is_empty() -> None:
    assert merge_tracks({}) == []
    assert merge_tracks({"voce": [], "outros": []}) == []


def test_merge_ties_keep_dict_insertion_order() -> None:
    result = merge_tracks(
        {
            "voce": [_seg(1000, 2000, "junto")],
            "outros": [_seg(1000, 2000, "também junto")],
        }
    )

    assert [segment.speaker for segment in result] == ["voce", "outros"]
