"""Interface de linha de comando. Ver docs/11-cli.md."""

from __future__ import annotations

import typer

from cronista.client import api_client, token_store

app = typer.Typer(add_completion=False)


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


if __name__ == "__main__":
    app()
