"""Wrapper isolado sobre faster-whisper: carrega o modelo e transcreve uma
trilha. Sem banco, sem fila — a orquestração de reunião inteira (leitura de
múltiplas trilhas, mesclagem, persistência) fica em cima disto
(docs/12-transcricao.md §7).

Ver docs/12-transcricao.md §3-4 (modelo, VAD e vocabulário) e §8 (config).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from faster_whisper import WhisperModel

# Caminho fixo dentro do container, ligado ao volume nomeado
# "whisper-models" do docker-compose.yml — não é configurável via
# WorkerSettings porque, como DATA_ROOT -> /data (docs/12 §8), é uma
# convenção de container, não uma escolha do usuário. Evita rebaixar ~3 GB
# de novo a cada rebuild de imagem.
MODEL_CACHE_DIR = "/models"


@dataclass(frozen=True)
class TranscribedSegment:
    start_ms: int
    end_ms: int
    text: str


def load_model(model_size: str, compute_type: str, device: str = "auto") -> WhisperModel:
    """Carrega o modelo Whisper (docs/12-transcricao.md §3).

    `device="auto"` deixa o ctranslate2 escolher CUDA quando disponível e
    cair para CPU fora do container do worker (ex.: testes no host).
    """
    return WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        download_root=MODEL_CACHE_DIR,
    )


def transcribe_track(
    model: WhisperModel,
    path: Path,
    language: str,
    vocabulary: str = "",
) -> list[TranscribedSegment]:
    """Transcreve uma trilha e devolve os segmentos em ordem.

    VAD sempre ativado (docs/12-transcricao.md §3): a trilha de loopback
    fica muda sempre que só o usuário fala, e submeter silêncio ao modelo
    custa tempo e induz alucinação. `vocabulary`, quando não vazio, vira o
    `initial_prompt` que influencia grafia de termos de domínio (§4, RF-13).
    """
    segments, _info = model.transcribe(
        str(path),
        language=language,
        vad_filter=True,
        initial_prompt=vocabulary or None,
    )
    return [
        TranscribedSegment(
            start_ms=round(segment.start * 1000),
            end_ms=round(segment.end * 1000),
            text=segment.text.strip(),
        )
        for segment in segments
    ]
