"""Cliente HTTP para a API. Ver docs/09-api.md."""

from __future__ import annotations

import httpx2

from cronista.client import token_store
from cronista.core.config import ClientSettings

settings = ClientSettings()


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _post(path: str, json_body: dict, access_token: str | None = None) -> httpx2.Response:
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    try:
        return httpx2.post(
            f"{settings.api_base_url}{path}", json=json_body, headers=headers, timeout=10.0
        )
    except httpx2.ConnectError as exc:
        raise ApiError(
            "Não foi possível conectar à API. Verifique se o container está no ar."
        ) from exc


def _raise_for_status(resp: httpx2.Response) -> None:
    try:
        resp.raise_for_status()
    except httpx2.HTTPStatusError as exc:
        raise ApiError(str(exc), status_code=resp.status_code) from exc


def login(username: str, password: str) -> dict[str, str]:
    resp = _post("/auth/login", {"username": username, "password": password})
    if resp.status_code == 401:
        raise ApiError("Usuário ou senha incorretos.", status_code=401)
    _raise_for_status(resp)
    return resp.json()


def refresh(refresh_token: str) -> str:
    resp = _post("/auth/refresh", {"refresh_token": refresh_token})
    if resp.status_code == 401:
        raise ApiError("Sessão expirada. Faça login novamente.", status_code=401)
    _raise_for_status(resp)
    return resp.json()["access_token"]


def _authed_post(path: str, json_body: dict) -> dict:
    """POST autenticado com renovação silenciosa (docs/11-cli.md §3): um
    401 tenta `refresh` uma vez antes de desistir, sem pedir senha de novo."""
    tokens = token_store.load_tokens()
    if tokens is None:
        raise ApiError("Não autenticado. Rode `cronista login`.", status_code=401)

    resp = _post(path, json_body, tokens["access_token"])
    if resp.status_code == 401:
        new_access_token = refresh(tokens["refresh_token"])
        token_store.save_tokens(new_access_token, tokens["refresh_token"])
        resp = _post(path, json_body, new_access_token)

    _raise_for_status(resp)
    return resp.json()


def create_meeting(payload: dict) -> dict:
    return _authed_post("/meetings", payload)


def register_track(meeting_id: object, payload: dict) -> dict:
    return _authed_post(f"/meetings/{meeting_id}/tracks", payload)


def reprocessar(meeting_id: object) -> dict:
    """UC-05, RF-15 (docs/12-transcricao.md §10)."""
    return _authed_post(f"/meetings/{meeting_id}/transcribe", {})
