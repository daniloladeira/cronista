"""Testes de `cronista importar` (UC-04). `conversion` e `registration`
são substituídos -- o alvo é a orquestração em `cli.py`, não ffmpeg de
verdade (isso é `tests/test_conversion.py`) nem hardware."""

from __future__ import annotations

from typer.testing import CliRunner

from cronista.client import cli, conversion, reconciliation, registration
from cronista.client.conversion import ConversionError, ProbeResult

runner = CliRunner()


def _stub_conversion(monkeypatch, duration_ms=60_000):
    monkeypatch.setattr(conversion, "require_ffmpeg", lambda: None)
    monkeypatch.setattr(conversion, "probe", lambda path: ProbeResult(has_audio=True, duration_ms=duration_ms))

    def _convert(input_path, output_path):
        output_path.write_bytes(b"fake wav")

    monkeypatch.setattr(conversion, "convert_to_wav", _convert)


def test_importar_com_sucesso_registra_e_informa_id(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    origem = tmp_path / "reuniao.mp4"
    origem.write_bytes(b"fake")
    _stub_conversion(monkeypatch)
    monkeypatch.setattr(registration, "register", lambda meeting, tracks, data_root: "recorded")
    monkeypatch.setattr(
        reconciliation, "reconcile", lambda data_root: {"reconciliadas": 0, "ainda_pendentes": 0, "inconsistentes": 0}
    )

    result = runner.invoke(cli.app, ["importar", str(origem), "--titulo", "Reunião Importada"])

    assert result.exit_code == 0
    assert "Reunião registrada" in result.stdout


def test_importar_monta_payload_com_source_import_e_falante_desconhecido(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    origem = tmp_path / "reuniao.mp4"
    origem.write_bytes(b"fake")
    _stub_conversion(monkeypatch, duration_ms=123_000)
    monkeypatch.setattr(
        reconciliation, "reconcile", lambda data_root: {"reconciliadas": 0, "ainda_pendentes": 0, "inconsistentes": 0}
    )
    captured = {}

    def _register(meeting, tracks, data_root):
        captured["meeting"] = meeting
        captured["tracks"] = tracks
        return "recorded"

    monkeypatch.setattr(registration, "register", _register)

    runner.invoke(cli.app, ["importar", str(origem)])

    assert captured["meeting"]["source"] == "import"
    assert captured["meeting"]["expected_tracks"] == 1
    assert captured["meeting"]["duration_ms"] == 123_000
    assert len(captured["tracks"]) == 1
    assert captured["tracks"][0]["speaker"] == "desconhecido"


def test_importar_sem_titulo_usa_nome_do_arquivo(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    origem = tmp_path / "gravacao-cliente-x.mp4"
    origem.write_bytes(b"fake")
    _stub_conversion(monkeypatch)
    monkeypatch.setattr(
        reconciliation, "reconcile", lambda data_root: {"reconciliadas": 0, "ainda_pendentes": 0, "inconsistentes": 0}
    )
    captured = {}
    monkeypatch.setattr(
        registration, "register", lambda meeting, tracks, data_root: captured.setdefault("meeting", meeting) and "recorded"
    )

    runner.invoke(cli.app, ["importar", str(origem)])

    assert captured["meeting"]["title"] == "gravacao-cliente-x"


def test_importar_com_api_fora_avisa_pendencia_sem_falhar(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    origem = tmp_path / "reuniao.mp4"
    origem.write_bytes(b"fake")
    _stub_conversion(monkeypatch)
    monkeypatch.setattr(registration, "register", lambda meeting, tracks, data_root: "pendente_envio")

    result = runner.invoke(cli.app, ["importar", str(origem)])

    assert result.exit_code == 0  # UC-04, mesma tolerância de rede que UC-10 já dá pra rec
    assert "pendente" in result.stdout.lower()


def test_importar_arquivo_inexistente_sai_com_codigo_4(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))

    result = runner.invoke(cli.app, ["importar", str(tmp_path / "nao-existe.mp4")])

    assert result.exit_code == 4
    assert "não encontrado" in result.output.lower()


def test_importar_com_ffmpeg_ausente_sai_com_codigo_4(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    origem = tmp_path / "reuniao.mp4"
    origem.write_bytes(b"fake")

    def _sem_ffmpeg():
        raise ConversionError("ffmpeg não encontrado.")

    monkeypatch.setattr(conversion, "require_ffmpeg", _sem_ffmpeg)

    result = runner.invoke(cli.app, ["importar", str(origem)])

    assert result.exit_code == 4
    assert "ffmpeg" in result.output.lower()


def test_importar_sem_faixa_de_audio_sai_com_codigo_4(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    origem = tmp_path / "video-mudo.mp4"
    origem.write_bytes(b"fake")
    monkeypatch.setattr(conversion, "require_ffmpeg", lambda: None)

    def _sem_audio(path):
        raise ConversionError(f"'{path}' não tem nenhuma faixa de áudio.")

    monkeypatch.setattr(conversion, "probe", _sem_audio)

    result = runner.invoke(cli.app, ["importar", str(origem)])

    assert result.exit_code == 4
    assert "áudio" in result.output.lower()


def test_importar_falha_na_conversao_sai_com_codigo_4(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    origem = tmp_path / "corrompido.mp3"
    origem.write_bytes(b"fake")
    monkeypatch.setattr(conversion, "require_ffmpeg", lambda: None)
    monkeypatch.setattr(conversion, "probe", lambda path: ProbeResult(has_audio=True, duration_ms=1000))

    def _falha_conversao(input_path, output_path):
        raise ConversionError(f"Falha convertendo '{input_path}'.")

    monkeypatch.setattr(conversion, "convert_to_wav", _falha_conversao)

    result = runner.invoke(cli.app, ["importar", str(origem)])

    assert result.exit_code == 4
