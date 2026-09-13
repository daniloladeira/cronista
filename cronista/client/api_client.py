"""Cliente HTTP para a API. Ver docs/09-api.md."""

from __future__ import annotations

import httpx2

from cronista.client import token_store
from cronista.client.settings import ClientSettings

settings = ClientSettings()


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _post(
    path: str, json_body: dict, access_token: str | None = None, timeout: float = 10.0
) -> httpx2.Response:
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    try:
        return httpx2.post(
            f"{settings.api_base_url}{path}", json=json_body, headers=headers, timeout=timeout
        )
    except httpx2.ConnectError as exc:
        raise ApiError(
            "Não foi possível conectar à API. Verifique se o container está no ar."
        ) from exc


def _get(
    path: str, params: dict | None = None, access_token: str | None = None, timeout: float = 10.0
) -> httpx2.Response:
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    try:
        return httpx2.get(
            f"{settings.api_base_url}{path}", params=params, headers=headers, timeout=timeout
        )
    except httpx2.ConnectError as exc:
        raise ApiError(
            "Não foi possível conectar à API. Verifique se o container está no ar."
        ) from exc


def _patch(path: str, json_body: dict, access_token: str | None = None, timeout: float = 10.0) -> httpx2.Response:
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    try:
        return httpx2.patch(
            f"{settings.api_base_url}{path}", json=json_body, headers=headers, timeout=timeout
        )
    except httpx2.ConnectError as exc:
        raise ApiError(
            "Não foi possível conectar à API. Verifique se o container está no ar."
        ) from exc


def _delete(path: str, access_token: str | None = None, timeout: float = 10.0) -> httpx2.Response:
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    try:
        return httpx2.delete(f"{settings.api_base_url}{path}", headers=headers, timeout=timeout)
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


def _authed_post(path: str, json_body: dict, timeout: float = 10.0) -> dict:
    """POST autenticado com renovação silenciosa (docs/11-cli.md §3): um
    401 tenta `refresh` uma vez antes de desistir, sem pedir senha de novo."""
    tokens = token_store.load_tokens()
    if tokens is None:
        raise ApiError("Não autenticado. Rode `cronista login`.", status_code=401)

    resp = _post(path, json_body, tokens["access_token"], timeout=timeout)
    if resp.status_code == 401:
        new_access_token = refresh(tokens["refresh_token"])
        token_store.save_tokens(new_access_token, tokens["refresh_token"])
        resp = _post(path, json_body, new_access_token, timeout=timeout)

    _raise_for_status(resp)
    return resp.json()


def _authed_get(path: str, params: dict | None = None, timeout: float = 10.0) -> dict:
    """GET autenticado com renovação silenciosa -- mesmo padrão de
    `_authed_post` (docs/11-cli.md §3)."""
    tokens = token_store.load_tokens()
    if tokens is None:
        raise ApiError("Não autenticado. Rode `cronista login`.", status_code=401)

    resp = _get(path, params, tokens["access_token"], timeout=timeout)
    if resp.status_code == 401:
        new_access_token = refresh(tokens["refresh_token"])
        token_store.save_tokens(new_access_token, tokens["refresh_token"])
        resp = _get(path, params, new_access_token, timeout=timeout)

    _raise_for_status(resp)
    return resp.json()


def _authed_patch(path: str, json_body: dict, timeout: float = 10.0) -> dict:
    """PATCH autenticado com renovação silenciosa -- mesmo padrão de
    `_authed_post` (docs/11-cli.md §3)."""
    tokens = token_store.load_tokens()
    if tokens is None:
        raise ApiError("Não autenticado. Rode `cronista login`.", status_code=401)

    resp = _patch(path, json_body, tokens["access_token"], timeout=timeout)
    if resp.status_code == 401:
        new_access_token = refresh(tokens["refresh_token"])
        token_store.save_tokens(new_access_token, tokens["refresh_token"])
        resp = _patch(path, json_body, new_access_token, timeout=timeout)

    _raise_for_status(resp)
    return resp.json()


def _authed_delete(path: str, timeout: float = 10.0) -> None:
    """DELETE autenticado com renovação silenciosa -- mesmo padrão de
    `_authed_patch` (docs/11-cli.md §3). Sem `.json()` no retorno: 204
    não tem corpo."""
    tokens = token_store.load_tokens()
    if tokens is None:
        raise ApiError("Não autenticado. Rode `cronista login`.", status_code=401)

    resp = _delete(path, tokens["access_token"], timeout=timeout)
    if resp.status_code == 401:
        new_access_token = refresh(tokens["refresh_token"])
        token_store.save_tokens(new_access_token, tokens["refresh_token"])
        resp = _delete(path, new_access_token, timeout=timeout)

    _raise_for_status(resp)


def create_meeting(payload: dict) -> dict:
    return _authed_post("/meetings", payload)


def register_track(meeting_id: object, payload: dict) -> dict:
    return _authed_post(f"/meetings/{meeting_id}/tracks", payload)


def reprocessar(meeting_id: object) -> dict:
    """UC-05, RF-15 (docs/12-transcricao.md §10)."""
    return _authed_post(f"/meetings/{meeting_id}/transcribe", {})


def resumir(meeting_id: object) -> dict:
    """UC-06, RF-16. Bloqueia até o provedor responder -- timeout bem
    maior que o padrão, um LLM local demora mais que 10s pra gerar."""
    return _authed_post(f"/meetings/{meeting_id}/summarize", {}, timeout=300.0)


def list_meetings() -> list[dict]:
    """RF-20, UC-07."""
    return _authed_get("/meetings")


def get_meeting(meeting_id: object) -> dict:
    """RF-20/RF-22, UC-07: dados da reunião com trilhas e resumos."""
    return _authed_get(f"/meetings/{meeting_id}")


def get_transcript(meeting_id: object) -> list[dict]:
    """RF-21, UC-07."""
    return _authed_get(f"/meetings/{meeting_id}/transcript")


def rename_meeting(meeting_id: object, title: str) -> dict:
    """UC-07."""
    return _authed_patch(f"/meetings/{meeting_id}", {"title": title})


def delete_meeting(meeting_id: object) -> None:
    """RF-30, UC-09. A confirmação é responsabilidade de quem chama
    (CLI) -- esta função, uma vez chamada, remove sem mais perguntas."""
    _authed_delete(f"/meetings/{meeting_id}")


def search(
    q: str, speaker: str | None = None, since: str | None = None, until: str | None = None
) -> list[dict]:
    """RF-23/RF-24, UC-08."""
    params = {"q": q}
    if speaker is not None:
        params["speaker"] = speaker
    if since is not None:
        params["since"] = since
    if until is not None:
        params["until"] = until
    return _authed_get("/search", params)
