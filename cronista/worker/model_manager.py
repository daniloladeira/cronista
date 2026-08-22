"""Ciclo de vida do modelo Whisper: carrega sob demanda, descarrega depois
de ociosidade (ADR-0014, docs/12-transcricao.md §3.1, §8), e tenta uma
segunda vez com quantização menor se faltar memória de GPU (§9).
"""

from __future__ import annotations

import logging
import time

from faster_whisper import WhisperModel

from cronista.core.config import WorkerSettings
from cronista.worker.transcription import load_model

logger = logging.getLogger(__name__)


def is_out_of_memory(exc: Exception) -> bool:
    """Heurística por mensagem -- ctranslate2 não expõe uma classe de
    exceção própria pra falta de memória de GPU, só um RuntimeError com o
    texto do erro CUDA embutido. Não verificado contra um OOM real de
    CUDA (difícil de forçar de forma confiável); a mensagem-padrão
    reportada pela comunidade do ctranslate2/faster-whisper contém
    "out of memory", em inglês, então o casamento é case-insensitive."""
    return "out of memory" in str(exc).lower()


class FallbackExhausted(RuntimeError):
    """OOM aconteceu já usando WHISPER_FALLBACK_COMPUTE_TYPE -- não há
    mais degradação possível, é falha como qualquer outra (docs/12 §9)."""


class ModelManager:
    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._model: WhisperModel | None = None
        self._using_fallback = False
        self._last_used = time.monotonic()

    def acquire(self) -> WhisperModel:
        """Devolve o modelo carregado, carregando agora se preciso. Falta
        de memória no carregamento tenta uma vez com a quantização de
        fallback antes de desistir (§9)."""
        if self._model is None:
            self._model = self._load(self._settings.whisper_compute_type)
        self._last_used = time.monotonic()
        return self._model

    def _load(self, compute_type: str) -> WhisperModel:
        try:
            return load_model(self._settings.whisper_model, compute_type)
        except Exception as exc:
            if not is_out_of_memory(exc) or compute_type == self._settings.whisper_fallback_compute_type:
                raise
            logger.warning(
                "Falta de memória carregando %s (%s); tentando %s.",
                self._settings.whisper_model,
                compute_type,
                self._settings.whisper_fallback_compute_type,
            )
            self._using_fallback = True
            return self._load(self._settings.whisper_fallback_compute_type)

    def reload_with_fallback(self) -> WhisperModel:
        """§9: falta de memória durante a transcrição (não no carregamento)
        -- descarrega e recarrega com a quantização de fallback. Só uma
        vez: se já era o fallback, levanta `FallbackExhausted` em vez de
        tentar de novo (nunca troca de modelo, nunca entra em loop)."""
        if self._using_fallback:
            raise FallbackExhausted(
                f"falta de memória já usando {self._settings.whisper_fallback_compute_type}, "
                "sem mais quantização pra tentar"
            )
        self._model = None
        self._using_fallback = True
        self._model = load_model(
            self._settings.whisper_model, self._settings.whisper_fallback_compute_type
        )
        self._last_used = time.monotonic()
        return self._model

    def is_loaded(self) -> bool:
        """Usado pelo gatilho de resumo automático (docs/07-arquitetura.md
        §3-4.3): só dispara depois que o Whisper está fora da VRAM."""
        return self._model is not None

    def release_if_idle(self) -> bool:
        """Descarrega o modelo se ocioso por `WHISPER_IDLE_UNLOAD_SECONDS`
        (§8) -- libera VRAM pro worker de resumo (ADR-0014). Devolve se
        descarregou, só pra quem chama decidir se loga algo."""
        if self._model is None:
            return False
        idle = time.monotonic() - self._last_used
        if idle < self._settings.whisper_idle_unload_seconds:
            return False
        self._model = None
        self._using_fallback = False  # próxima carga volta à quantização normal
        return True
