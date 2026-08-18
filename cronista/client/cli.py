"""Interface de linha de comando. Ver docs/11-cli.md."""

from __future__ import annotations

import socket
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import jwt
import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from cronista.client import (
    api_client,
    banner,
    capture,
    naming,
    reconciliation,
    registration,
    signal_bar,
    token_store,
)
from cronista.client.reconciliation import ReconcileResult
from cronista.core.config import RECORDINGS_DIRNAME, ClientSettings
from cronista.core.ids import uuid7

app = typer.Typer(add_completion=False)
_console = Console()
_settings = ClientSettings()

_SUBTITLE_COLOR = "#F7ECDA"  # dourado bem claro
_MINIMAL_COLOR = "#A6A6A6"  # neutro, mesmo tom de "outros" (signal_bar.py)
_SUBTITLE = "Grava, transcreve e resume reuniões localmente."
_CATEGORIAS = "transcreva reuniões · resumos automáticos · anotações"
_COMANDOS_MINIMOS = [("r", "rec"), ("d", "devices"), ("s", "sync"), ("l", "login")]


def _usuario_logado() -> str:
    """Decodifica o `sub` do access token só pra exibir -- sem verificar
    assinatura, porque não faz sentido validar aqui: o cliente nunca tem
    o JWT_SECRET (ClientSettings é deliberadamente restrito, ver
    core/config.py), e a API já vai recusar o token na próxima chamada
    de rede se ele for inválido de verdade. Isto é só cosmético."""
    tokens = token_store.load_tokens()
    if tokens is None:
        return "não autenticado"
    try:
        payload = jwt.decode(tokens["access_token"], options={"verify_signature": False})
        return str(payload.get("sub", "autenticado"))
    except jwt.PyJWTError:
        return "autenticado"


def _tela_inicial_partes() -> list[Text]:
    # `cronista` sem comando: banner de abertura toda vez (docs/17
    # §3, §7) -- não é mais throttle de uma vez por dia, já que agora é
    # tela alternativa (some ao sair, sem poluir o histórico) em vez de
    # imprimir e ficar no scrollback. Resumo mínimo embaixo, não a tabela
    # de ajuda do Typer (`--help` explícito continua completo).
    partes: list[Text] = [Text(), banner.render(_console), Text()]
    partes.append(Text(_SUBTITLE, style=f"bold {_SUBTITLE_COLOR}"))
    partes.append(Text())
    partes.append(Text(_CATEGORIAS, style=_MINIMAL_COLOR))
    partes.append(Text())
    partes.append(Text(f"{_usuario_logado()} · {socket.gethostname()}", style=_MINIMAL_COLOR))
    partes.append(Text())
    comandos = "    ".join(f"{letra} - {nome}" for letra, nome in _COMANDOS_MINIMOS)
    partes.append(Text(comandos, style=_MINIMAL_COLOR))
    return partes


def _render_tela_inicial() -> None:
    """Alinhado à esquerda, de propósito -- duas tentativas de centralizar
    (`justify="center"`/`Align`) quebraram de verdade no terminal do
    usuário: texto cortado na borda em janela estreita, banner empurrado
    pra fora da tela em janela alta. Suspeita é `console.width`/`.height`
    do Rich não baterem com o tamanho real da janela nesse terminal, mas
    sem confirmar isso na máquina de verdade, mais seguro não depender de
    largura nem altura nenhuma pra posicionar (docs/17 §7)."""
    for parte in _tela_inicial_partes():
        _console.print(parte)


@app.callback(invoke_without_command=True)
def _callback(ctx: typer.Context) -> None:
    """Cronista: grava, transcreve e resume reuniões localmente."""
    if ctx.invoked_subcommand is not None:
        return
    if not _console.is_terminal:
        # Script, pipe, CI: sem terminal de verdade não tem quem aperte
        # Ctrl+C, e a tela alternativa não faz sentido nenhum aqui —
        # imprime uma vez e sai, como sempre foi nesse caso.
        _render_tela_inicial()
        return
    # Tela alternativa, igual ao `rec` (Live(..., screen=True)) -- some
    # ao sair, sem deixar rastro no histórico de rolagem. Ctrl+C é o
    # único jeito de sair, de propósito: nada pra navegar aqui.
    with _console.screen():
        _render_tela_inicial()
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass


@app.command()
def login(
    usuario: str = typer.Option(..., prompt=True),
    senha: str = typer.Option(..., prompt=True, hide_input=True),
) -> None:
    """Autentica e guarda os tokens localmente (UC-01)."""
    try:
        tokens = api_client.login(usuario, senha)
    except api_client.ApiError as exc:
        typer.echo(f"Erro: {exc}", err=True)
        raise typer.Exit(code=2 if exc.status_code == 401 else 3)

    token_store.save_tokens(tokens["access_token"], tokens["refresh_token"])
    typer.echo("Login realizado. Token salvo.")


def _report_reconciliation(resultado: ReconcileResult) -> None:
    if resultado["reconciliadas"]:
        typer.echo(f"{resultado['reconciliadas']} reunião(ões) pendente(s) reconciliada(s).")
    if resultado["ainda_pendentes"]:
        typer.echo(
            f"{resultado['ainda_pendentes']} reunião(ões) seguem pendentes — API indisponível."
        )
    if resultado["inconsistentes"]:
        typer.echo(
            f"Aviso: {resultado['inconsistentes']} pendência(s) com arquivo de áudio ausente. "
            "Precisa de conferência manual (UC-11 FE-02).",
            err=True,
        )


@app.command()
def sync() -> None:
    """Reenvia reuniões pendentes de envio (UC-11)."""
    resultado = reconciliation.reconcile(_settings.data_root)
    _report_reconciliation(resultado)  # FA-01: nada pendente, nada pra dizer


@app.command()
def devices() -> None:
    """Lista dispositivos de entrada e saída (UC-02). Não precisa da API."""
    entrada = Table(title="Entrada (microfone)")
    entrada.add_column("Nome")
    entrada.add_column("Padrão")
    for d in capture.list_input_devices():
        entrada.add_row(d.name, "sim" if d.is_default else "")
    _console.print(entrada)

    saida = Table(title="Saída (usada via loopback para a trilha 'outros')")
    saida.add_column("Nome")
    saida.add_column("Padrão")
    for d in capture.list_output_devices():
        saida.add_row(d.name, "sim" if d.is_default else "")
    _console.print(saida)


@app.command()
def rec(
    titulo: str = typer.Option(None, "--titulo", help="Título da reunião. Padrão: data e hora."),
    mic: str = typer.Option(
        None, "--mic", help="Nome do dispositivo de entrada. Padrão: microfone do sistema."
    ),
    saida: str = typer.Option(
        None, "--saida", help="Nome do dispositivo de saída (loopback). Padrão: saída do sistema."
    ),
) -> None:
    """Grava a reunião até Ctrl+C (UC-03). Funciona com a API fora do ar."""
    try:
        mic_device = capture.get_input_device(mic)  # None = sem microfone (UC-02 FE-01)
        speaker_device = capture.get_output_device(saida)
        loopback_device = capture.get_loopback_device(speaker_device)  # UC-02 FE-02
    except capture.DeviceError as exc:
        typer.echo(f"Erro: {exc}", err=True)
        raise typer.Exit(code=4)

    if mic_device is None:
        typer.echo(
            "Aviso: nenhum microfone disponível — gravando só a trilha 'outros'.", err=True
        )

    started_at = datetime.now(UTC)
    title = titulo or f"Reunião {started_at:%Y-%m-%d %H:%M}"  # UC-03 FA-01
    audio_dir = naming.make_audio_dir(title, started_at)
    output_dir = Path(_settings.data_root) / RECORDINGS_DIRNAME / audio_dir

    stop_event = threading.Event()
    pause_event = threading.Event()
    # ADR-0004: started_at é UTC (pro payload da API); a tela mostra hora
    # local, que é responsabilidade da apresentação, não do armazenamento.
    bar = signal_bar.SignalBar(title, started_at.astimezone(), console=_console)

    with bar:
        result = capture.record(
            output_dir,
            mic_device=mic_device,
            loopback_device=loopback_device,
            stop_event=stop_event,
            pause_event=pause_event,
            on_level=bar.update,
            on_pause_toggle=bar.set_paused,
        )
    ended_at = datetime.now(UTC)

    for track in result.tracks:
        if track.error:
            typer.echo(
                f"Aviso: trilha '{track.speaker}' interrompida ({track.error}). "
                "O que já foi gravado continua salvo.",
                err=True,
            )
        elif not track.had_signal:
            typer.echo(
                f"Aviso: trilha '{track.speaker}' não registrou sinal algum. "
                "Verifique o dispositivo.",
                err=True,
            )

    # UC-10 só recebe trilhas íntegras (FE-02): uma trilha sem áudio nenhum
    # não deve contar em expected_tracks, ou a reunião nunca sairia de
    # 'registering' — a trilha que falhou simplesmente não existe pra API.
    valid_tracks = [t for t in result.tracks if t.error is None]
    if not valid_tracks:
        typer.echo("Erro: nenhuma trilha foi gravada com sucesso.", err=True)
        raise typer.Exit(code=4)

    meeting_id = uuid7()
    meeting_payload = {
        "id": str(meeting_id),
        "title": title,
        "source": "capture",
        "host": socket.gethostname(),
        "audio_dir": audio_dir,
        "expected_tracks": len(valid_tracks),
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_ms": max(t.duration_ms for t in valid_tracks),
    }
    track_payloads = [
        {
            "speaker": t.speaker,
            "path": t.path.name,
            "sample_rate": capture.SAMPLE_RATE,
            "channels": capture.CHANNELS,
            "duration_ms": t.duration_ms,
            "size_bytes": t.size_bytes,
            "device": t.device,
        }
        for t in valid_tracks
    ]

    estado = registration.register(meeting_payload, track_payloads, _settings.data_root)

    typer.echo(f"Arquivos em: {output_dir}")
    if estado == "recorded":
        typer.echo(f"Reunião registrada: {meeting_id}")
        # docs/11-cli.md §3: "reconciliação é automática". Só faz sentido
        # tentar aqui, não antes de gravar (RN-08) — e só se a API acabou
        # de responder, senão é rede indisponível de novo, sem necessidade.
        _report_reconciliation(reconciliation.reconcile(_settings.data_root))
    else:
        # UC-03 FE-01/FE-02: não é erro (docs/11-cli.md §5) — o áudio já
        # está íntegro em disco, só o registro na API que fica pendente.
        typer.echo(
            "Áudio salvo, mas a API não confirmou o registro agora — fica pendente "
            "e será reenviado com `cronista sync` quando ela voltar."
        )


if __name__ == "__main__":
    app()
