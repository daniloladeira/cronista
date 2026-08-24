"""Interface de linha de comando. Ver docs/11-cli.md."""

from __future__ import annotations

import socket
import threading
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown as RichMarkdown
from rich.table import Table
from rich.text import Text

from cronista.client import (
    api_client,
    capture,
    conversion,
    home,
    naming,
    panel,
    reconciliation,
    registration,
    session_info,
    signal_bar,
    token_store,
)
from cronista.client.reconciliation import ReconcileResult
from cronista.core.config import RECORDINGS_DIRNAME, ClientSettings
from cronista.core.ids import uuid7

app = typer.Typer(add_completion=False)
_console = Console()
_settings = ClientSettings()

_COMANDOS_MINIMOS = [("r", "rec"), ("d", "devices"), ("s", "sync"), ("l", "login"), ("t", "list")]


def _tela_inicial_partes() -> list[Text]:
    # `cronista` sem comando, fora de terminal interativo: mesmo conteúdo
    # do menu navegável (home.py), só que estático -- não tem quem
    # aperte seta/Enter num script ou pipe.
    partes = session_info.partes(_console)
    partes.append(Text())
    comandos = "    ".join(f"{letra} - {nome}" for letra, nome in _COMANDOS_MINIMOS)
    partes.append(Text(comandos, style=session_info.MINIMAL_COLOR))
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
        # Script, pipe, CI: sem terminal de verdade não tem quem navegue
        # um menu Textual -- imprime uma vez e sai, como sempre foi.
        _render_tela_inicial()
        return
    # Menu navegável (ADR-0016, seção "Extensão"). É só um seletor: sai
    # completamente (self.exit) antes do comando escolhido rodar --
    # nenhum comando roda dentro dele, `rec` continua fora de qualquer
    # loop de evento (ADR-0006).
    chosen = home.HomeApp().run()
    if chosen is None:
        return  # Escape/q: usuário saiu sem escolher nada
    if chosen == "rec":
        # rec() chamado direto (fora do Click) não resolve os defaults de
        # typer.Option pra None sozinho -- precisa passar explícito, senão
        # capture.get_input_device recebe o próprio objeto OptionInfo.
        rec(titulo=None, mic=None, saida=None)
    elif chosen == "devices":
        devices()
    elif chosen == "sync":
        sync()
    elif chosen == "login":
        usuario = typer.prompt("Usuario")
        senha = typer.prompt("Senha", hide_input=True)
        _do_login(usuario, senha)
    elif chosen == "list":
        list_()


def _do_login(usuario: str, senha: str) -> None:
    try:
        tokens = api_client.login(usuario, senha)
    except api_client.ApiError as exc:
        typer.echo(f"Erro: {exc}", err=True)
        raise typer.Exit(code=2 if exc.status_code == 401 else 3)

    token_store.save_tokens(tokens["access_token"], tokens["refresh_token"])
    typer.echo("Login realizado. Token salvo.")


@app.command()
def login(
    usuario: str = typer.Option(..., prompt=True),
    senha: str = typer.Option(..., prompt=True, hide_input=True),
) -> None:
    """Autentica e guarda os tokens localmente (UC-01)."""
    _do_login(usuario, senha)


@app.command()
def reprocessar(meeting_id: str = typer.Argument(..., help="ID da reunião")) -> None:
    """Retranscreve, substituindo os segmentos antigos (UC-05, RF-15)."""
    try:
        api_client.reprocessar(meeting_id)
    except api_client.ApiError as exc:
        typer.echo(f"Erro: {exc}", err=True)
        if exc.status_code == 404:
            raise typer.Exit(code=1)
        if exc.status_code == 409:
            raise typer.Exit(code=5)
        raise typer.Exit(code=2 if exc.status_code == 401 else 3)

    typer.echo("Reunião marcada para reprocessamento — o worker pega na próxima passada.")


@app.command()
def resumir(meeting_id: str = typer.Argument(..., help="ID da reunião")) -> None:
    """Gera um novo resumo (UC-06, RF-16). Bloqueia até o provedor responder."""
    try:
        resultado = api_client.resumir(meeting_id)
    except api_client.ApiError as exc:
        typer.echo(f"Erro: {exc}", err=True)
        if exc.status_code == 404:
            raise typer.Exit(code=1)
        if exc.status_code == 409:
            raise typer.Exit(code=5)
        raise typer.Exit(code=2 if exc.status_code == 401 else 3)

    typer.echo(resultado["markdown"])


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


@app.command()
def importar(
    arquivo: str = typer.Argument(..., help="Caminho do arquivo de áudio ou vídeo."),
    titulo: str = typer.Option(None, "--titulo", help="Título da reunião. Padrão: nome do arquivo."),
) -> None:
    """Importa um arquivo de áudio ou vídeo preexistente (UC-04). Converte
    pro formato interno (RN-09) e segue o mesmo caminho de registro que
    `rec` usa (UC-10) -- falante único `desconhecido` (RN-02)."""
    caminho = Path(arquivo)
    if not caminho.is_file():
        typer.echo(f"Erro: arquivo '{arquivo}' não encontrado.", err=True)
        raise typer.Exit(code=4)

    try:
        conversion.require_ffmpeg()
        resultado_probe = conversion.probe(caminho)
    except conversion.ConversionError as exc:
        typer.echo(f"Erro: {exc}", err=True)
        raise typer.Exit(code=4)

    started_at = datetime.now(UTC)
    title = titulo or caminho.stem
    audio_dir = naming.make_audio_dir(title, started_at)
    output_dir = Path(_settings.data_root) / RECORDINGS_DIRNAME / audio_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    track_path = output_dir / "desconhecido.wav"

    try:
        conversion.convert_to_wav(caminho, track_path)
    except conversion.ConversionError as exc:
        typer.echo(f"Erro: {exc}", err=True)
        raise typer.Exit(code=4)

    meeting_id = uuid7()
    meeting_payload = {
        "id": str(meeting_id),
        "title": title,
        "source": "import",
        "host": socket.gethostname(),
        "audio_dir": audio_dir,
        "expected_tracks": 1,
        "started_at": started_at.isoformat(),
        "ended_at": started_at.isoformat(),
        "duration_ms": resultado_probe.duration_ms,
    }
    track_payloads = [
        {
            "speaker": "desconhecido",
            "path": track_path.name,
            "sample_rate": 16_000,
            "channels": 1,
            "duration_ms": resultado_probe.duration_ms,
            "size_bytes": track_path.stat().st_size,
            "device": None,
        }
    ]

    estado = registration.register(meeting_payload, track_payloads, _settings.data_root)

    typer.echo(f"Arquivos em: {output_dir}")
    if estado == "recorded":
        typer.echo(f"Reunião registrada: {meeting_id}")
        _report_reconciliation(reconciliation.reconcile(_settings.data_root))
    else:
        typer.echo(
            "Áudio salvo, mas a API não confirmou o registro agora — fica pendente "
            "e será reenviado com `cronista sync` quando ela voltar."
        )


def _tabela_reunioes(reunioes: list[dict], titulo: str) -> Table:
    tabela = Table(title=titulo)
    tabela.add_column("Título")
    tabela.add_column("Estado")
    tabela.add_column("Início")
    for r in reunioes:
        tabela.add_row(r["title"], r["status"], r["started_at"])
    return tabela


@app.command(name="list")
def list_() -> None:
    """Lista reuniões, e navega entre elas (UC-07, ADR-0016)."""
    if not _console.is_terminal:
        _console.print(_tabela_reunioes(api_client.list_meetings(), "Reuniões"))
        return
    panel.PanelApp().run()


@app.command()
def ler(meeting_id: str = typer.Argument(..., help="ID da reunião")) -> None:
    """Abre uma reunião já focada, com transcrição e resumo (UC-07, ADR-0016)."""
    if not _console.is_terminal:
        reuniao = api_client.get_meeting(meeting_id)
        segmentos = api_client.get_transcript(meeting_id)
        for s in segmentos:
            _console.print(f"[{s['timestamp']}] {s['speaker']}: {s['text']}")
        resumos = reuniao.get("summaries") or []
        if resumos:
            mais_recente = sorted(resumos, key=lambda r: r["generated_at"])[-1]
            _console.print(RichMarkdown(mais_recente["markdown"]))
        return
    panel.PanelApp(meeting_id=meeting_id).run()


@app.command()
def buscar(termo: str = typer.Argument(..., help="Termo de busca")) -> None:
    """Busca por conteúdo em todas as transcrições, com stemming de
    português (UC-08, RF-23/24, ADR-0016)."""
    if not _console.is_terminal:
        resultados = api_client.search(termo)
        tabela = Table(title=f'Busca: "{termo}"')
        tabela.add_column("Reunião")
        tabela.add_column("Instante")
        tabela.add_column("Falante")
        tabela.add_column("Trecho")
        for r in resultados:
            tabela.add_row(r["meeting_title"], r["timestamp"], r["speaker"], r["text"])
        _console.print(tabela)
        return
    panel.PanelApp(search_term=termo).run()


if __name__ == "__main__":
    app()
