"""Testes de `cronista rec` e `cronista devices` (UC-02, UC-03).

Nem hardware de áudio nem API de verdade: `capture.record`/`get_*_device`
e `registration.register` são substituídos. O alvo é a orquestração em
`cli.py` — que payload monta, como reage a cada desfecho de UC-10.
"""

from __future__ import annotations

from typer.testing import CliRunner

from cronista.client import capture, cli, reconciliation, registration
from cronista.client.capture import DeviceInfo, RecordingResult, TrackResult

runner = CliRunner()


def _tracks_ok(tmp_path):
    voce = tmp_path / "voce.wav"
    outros = tmp_path / "outros.wav"
    voce.write_bytes(b"fake")
    outros.write_bytes(b"fake")
    return [
        TrackResult("voce", voce, "Mic Fake", 60_000, 4, True),
        TrackResult("outros", outros, "Speaker Fake", 60_000, 4, True),
    ]


def _stub_devices(monkeypatch):
    monkeypatch.setattr(capture, "get_input_device", lambda name=None: object())
    monkeypatch.setattr(capture, "get_output_device", lambda name=None: object())
    monkeypatch.setattr(capture, "get_loopback_device", lambda speaker: object())


def test_rec_com_sucesso_registra_e_informa_id(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    _stub_devices(monkeypatch)
    monkeypatch.setattr(
        capture, "record", lambda *a, **k: RecordingResult(tracks=_tracks_ok(tmp_path))
    )
    monkeypatch.setattr(registration, "register", lambda meeting, tracks, data_root: "recorded")

    result = runner.invoke(cli.app, ["rec", "--titulo", "Reunião de Teste"])

    assert result.exit_code == 0
    assert "Reunião registrada" in result.stdout


def test_rec_com_sucesso_tambem_reconcilia_outras_pendencias(monkeypatch, tmp_path):
    # docs/11-cli.md §3: reconciliação automática acontece DEPOIS de gravar
    # (RN-08), e só quando a própria reunião confirmou com a API.
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    _stub_devices(monkeypatch)
    monkeypatch.setattr(
        capture, "record", lambda *a, **k: RecordingResult(tracks=_tracks_ok(tmp_path))
    )
    monkeypatch.setattr(registration, "register", lambda meeting, tracks, data_root: "recorded")
    monkeypatch.setattr(
        reconciliation,
        "reconcile",
        lambda data_root: {"reconciliadas": 3, "ainda_pendentes": 0, "inconsistentes": 0},
    )

    result = runner.invoke(cli.app, ["rec"])

    assert result.exit_code == 0
    assert "3" in result.stdout


def test_rec_com_api_fora_nao_tenta_reconciliar(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    _stub_devices(monkeypatch)
    monkeypatch.setattr(
        capture, "record", lambda *a, **k: RecordingResult(tracks=_tracks_ok(tmp_path))
    )
    monkeypatch.setattr(
        registration, "register", lambda meeting, tracks, data_root: "pendente_envio"
    )

    chamou = False

    def _reconcile(data_root):
        nonlocal chamou
        chamou = True
        return {"reconciliadas": 0, "ainda_pendentes": 0, "inconsistentes": 0}

    monkeypatch.setattr(reconciliation, "reconcile", _reconcile)

    runner.invoke(cli.app, ["rec"])

    assert not chamou  # API já sabidamente fora, não vale a pena tentar de novo


def test_rec_com_api_fora_avisa_pendencia_sem_falhar(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    _stub_devices(monkeypatch)
    monkeypatch.setattr(
        capture, "record", lambda *a, **k: RecordingResult(tracks=_tracks_ok(tmp_path))
    )
    monkeypatch.setattr(
        registration, "register", lambda meeting, tracks, data_root: "pendente_envio"
    )

    result = runner.invoke(cli.app, ["rec"])

    assert result.exit_code == 0  # UC-03 FE-01: não é erro
    assert "pendente" in result.stdout.lower()


def test_rec_sem_microfone_avisa_e_grava_so_outros(monkeypatch, tmp_path):
    # CT-05 / UC-02 FE-01: sem microfone é degradação esperada, não erro.
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    monkeypatch.setattr(capture, "get_input_device", lambda name=None: None)
    monkeypatch.setattr(capture, "get_output_device", lambda name=None: object())
    monkeypatch.setattr(capture, "get_loopback_device", lambda speaker: object())

    outros = tmp_path / "outros.wav"
    outros.write_bytes(b"fake")
    recebido = {}

    def _record(output_dir, mic_device, loopback_device, **kwargs):
        recebido["mic_device"] = mic_device
        return RecordingResult(tracks=[TrackResult("outros", outros, "Speaker Fake", 60_000, 4, True)])

    monkeypatch.setattr(capture, "record", _record)
    monkeypatch.setattr(registration, "register", lambda meeting, tracks, data_root: "recorded")
    monkeypatch.setattr(reconciliation, "reconcile", lambda data_root: {
        "reconciliadas": 0, "ainda_pendentes": 0, "inconsistentes": 0
    })

    result = runner.invoke(cli.app, ["rec"])

    assert result.exit_code == 0
    assert recebido["mic_device"] is None  # None chega intacto até capture.record
    assert "nenhum microfone" in result.output.lower()
    assert "reunião registrada" in result.output.lower()


def test_rec_com_saida_sem_loopback_sai_com_codigo_4(monkeypatch):
    # CT-06 / UC-02 FE-02.
    monkeypatch.setattr(capture, "get_input_device", lambda name=None: object())
    monkeypatch.setattr(capture, "get_output_device", lambda name=None: object())

    def _falha_loopback(speaker):
        raise capture.DeviceError("'Alto-falantes' não expõe captura de loopback.")

    monkeypatch.setattr(capture, "get_loopback_device", _falha_loopback)

    result = runner.invoke(cli.app, ["rec"])

    assert result.exit_code == 4
    assert "loopback" in result.output.lower()


def test_rec_com_dispositivo_invalido_sai_com_codigo_4(monkeypatch):
    def _falha(name=None):
        raise capture.DeviceError(f"Dispositivo '{name}' não encontrado.")

    monkeypatch.setattr(capture, "get_input_device", _falha)

    result = runner.invoke(cli.app, ["rec", "--mic", "Fantasma"])

    assert result.exit_code == 4


def test_rec_com_todas_as_trilhas_falhas_sai_com_codigo_4(monkeypatch, tmp_path):
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    _stub_devices(monkeypatch)
    falhas = RecordingResult(
        tracks=[
            TrackResult(
                "voce", tmp_path / "voce.wav", "Mic", 0, 0, False, error="dispositivo removido"
            ),
            TrackResult(
                "outros",
                tmp_path / "outros.wav",
                "Speaker",
                0,
                0,
                False,
                error="dispositivo removido",
            ),
        ]
    )
    monkeypatch.setattr(capture, "record", lambda *a, **k: falhas)

    result = runner.invoke(cli.app, ["rec"])

    assert result.exit_code == 4


def test_rec_expected_tracks_exclui_trilha_com_erro(monkeypatch, tmp_path):
    # A trilha sem áudio não pode contar em expected_tracks (docs/08 §5) —
    # senão a reunião nunca sairia de 'registering' na API.
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    _stub_devices(monkeypatch)
    voce = tmp_path / "voce.wav"
    voce.write_bytes(b"fake")
    mixed = RecordingResult(
        tracks=[
            TrackResult("voce", voce, "Mic", 60_000, 4, True),
            TrackResult(
                "outros", tmp_path / "outros.wav", "Speaker", 0, 0, False, error="sumiu"
            ),
        ]
    )
    monkeypatch.setattr(capture, "record", lambda *a, **k: mixed)

    captured = {}

    def _register(meeting, tracks, data_root):
        captured["meeting"] = meeting
        captured["tracks"] = tracks
        return "recorded"

    monkeypatch.setattr(registration, "register", _register)

    result = runner.invoke(cli.app, ["rec"])

    assert result.exit_code == 0
    assert captured["meeting"]["expected_tracks"] == 1
    assert [t["speaker"] for t in captured["tracks"]] == ["voce"]


def test_rec_trilha_sem_sinal_avisa_o_usuario(monkeypatch, tmp_path):
    # CT-11.
    monkeypatch.setattr(cli._settings, "data_root", str(tmp_path))
    _stub_devices(monkeypatch)
    voce = tmp_path / "voce.wav"
    outros = tmp_path / "outros.wav"
    voce.write_bytes(b"fake")
    outros.write_bytes(b"fake")
    sem_sinal = RecordingResult(
        tracks=[
            TrackResult("voce", voce, "Mic", 60_000, 4, had_signal=False),
            TrackResult("outros", outros, "Speaker", 60_000, 4, had_signal=True),
        ]
    )
    monkeypatch.setattr(capture, "record", lambda *a, **k: sem_sinal)
    monkeypatch.setattr(registration, "register", lambda meeting, tracks, data_root: "recorded")
    monkeypatch.setattr(
        reconciliation,
        "reconcile",
        lambda data_root: {"reconciliadas": 0, "ainda_pendentes": 0, "inconsistentes": 0},
    )

    result = runner.invoke(cli.app, ["rec"])

    assert result.exit_code == 0
    assert "voce" in result.output.lower()
    assert "sinal" in result.output.lower()


def test_devices_lista_entrada_e_saida(monkeypatch):
    monkeypatch.setattr(
        capture, "list_input_devices", lambda: [DeviceInfo("Mic Fake", True)]
    )
    monkeypatch.setattr(
        capture, "list_output_devices", lambda: [DeviceInfo("Speaker Fake", False)]
    )

    result = runner.invoke(cli.app, ["devices"])

    assert result.exit_code == 0
    assert "Mic Fake" in result.stdout
    assert "Speaker Fake" in result.stdout
