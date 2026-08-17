"""Interface de linha de comando. Ver docs/11-cli.md."""

from __future__ import annotations

import socket
import threading
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from cronista.client import api_client, capture, naming, registration, signal_bar, token_store
from cronista.core.config import RECORDINGS_DIRNAME, ClientSettings
from cronista.core.ids import uuid7

app = typer.Typer(add_completion=False)
_console = Console()
_settings = ClientSettings()


@app.callback()
def _callback() -> None:
    """Cronista: grava, transcreve e resume reuniões localmente."""
    # Existe para impedir que o Typer colapse o único comando registrado
    # (login) em comando padrão do app, sem nome de subcomando. Some de
    # necessidade assim que a Fase 2 acrescentar mais comandos.


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
        mic_device = capture.get_input_device(mic)
        speaker_device = capture.get_output_device(saida)
    except capture.DeviceError as exc:
        typer.echo(f"Erro: {exc}", err=True)
        raise typer.Exit(code=4)

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
            speaker_device=speaker_device,
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
    else:
        # UC-03 FE-01/FE-02: não é erro (docs/11-cli.md §5) — o áudio já
        # está íntegro em disco, só o registro na API que fica pendente.
        typer.echo(
            "Áudio salvo, mas a API não confirmou o registro agora — fica pendente "
            "e será reenviado com `cronista sync` quando ela voltar."
        )


if __name__ == "__main__":
    app()
