"""Cliente HTTP para a API. Ver docs/09-api.md."""

from __future__ import annotations

import httpx2

from cronista.core.config import ClientSettings

settings = ClientSettings()


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def login(username: str, password: str) -> dict[str, str]:
    try:
        resp = httpx2.post(
            f"{settings.api_base_url}/auth/login",
            json={"username": username, "password": password},
            timeout=10.0,
        )
    except httpx2.ConnectError as exc:
        raise ApiError(
            "Não foi possível conectar à API. Verifique se o container está no ar."
        ) from exc

    if resp.status_code == 401:
        raise ApiError("Usuário ou senha incorretos.", status_code=401)
    resp.raise_for_status()
    return resp.json()
