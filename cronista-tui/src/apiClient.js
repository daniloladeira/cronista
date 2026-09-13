import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.join(__dirname, "..", "..");

export class ApiError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.statusCode = statusCode;
  }
}

// Lida uma vez só: API_BASE_URL não muda no meio do processo, então não
// há por que reabrir e reler o .env do disco a cada chamada de API.
let _apiBaseUrl = null;

function readApiBaseUrl() {
  if (_apiBaseUrl !== null) return _apiBaseUrl;
  // Variável de ambiente tem prioridade sobre o .env, igual
  // cronista/client/settings.py::ClientSettings -- sem isto, sobrepor
  // API_BASE_URL no ambiente funcionava pro cliente Python mas era
  // ignorado aqui do lado Ink.
  if (process.env.API_BASE_URL) {
    _apiBaseUrl = process.env.API_BASE_URL;
    return _apiBaseUrl;
  }
  const envPath = path.join(REPO_ROOT, ".env");
  const text = fs.readFileSync(envPath, "utf-8");
  const match = text.match(/^API_BASE_URL=(.*)$/m);
  if (!match) throw new Error(`API_BASE_URL não encontrado em ${envPath}`);
  _apiBaseUrl = match[1].trim();
  return _apiBaseUrl;
}

function tokenPath() {
  // Tem que ser o mesmo arquivo que token_store.py usa, não uma cópia --
  // senão `cronista login` (Python) e esta TUI (Node) teriam sessão
  // cada um por conta própria.
  const root = process.env.LOCALAPPDATA || os.homedir();
  return path.join(root, "cronista", "auth.json");
}

// Em cache depois da primeira leitura -- "Login" sempre sai do Ink e
// respawna um processo novo (ver index.js), então dentro da vida de um
// processo só este próprio saveTokens muda o arquivo; não há por que
// reabrir e reparsear auth.json a cada chamada autenticada (duas de uma
// vez, em paralelo, ao abrir uma reunião: getMeeting + getTranscript).
let _tokensCache;

function loadTokens() {
  if (_tokensCache !== undefined) return _tokensCache;
  const p = tokenPath();
  if (!fs.existsSync(p)) {
    _tokensCache = null;
    return _tokensCache;
  }
  const data = JSON.parse(fs.readFileSync(p, "utf-8"));
  _tokensCache = { accessToken: data.access_token, refreshToken: data.refresh_token };
  return _tokensCache;
}

function saveTokens(accessToken, refreshToken) {
  fs.writeFileSync(tokenPath(), JSON.stringify({ access_token: accessToken, refresh_token: refreshToken }));
  _tokensCache = { accessToken, refreshToken };
}

// fetch() nativo não tem timeout por padrão -- sem isso, uma porta que
// aceita conexão mas nunca responde trava a tela pra sempre.
const _TIMEOUT_MS = 10_000;

function _mensagemDeFalha(err) {
  if (err?.name === "TimeoutError") {
    return "Tempo esgotado conectando à API (10s). Verifique se o container está no ar e respondendo.";
  }
  return "Não foi possível conectar à API. Verifique se o container está no ar.";
}

async function request(method, apiPath, accessToken) {
  const base = readApiBaseUrl();
  let resp;
  try {
    resp = await fetch(`${base}${apiPath}`, {
      method,
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      signal: AbortSignal.timeout(_TIMEOUT_MS),
    });
  } catch (err) {
    throw new ApiError(_mensagemDeFalha(err));
  }
  return resp;
}

async function refresh(refreshToken) {
  const base = readApiBaseUrl();
  let resp;
  try {
    resp = await fetch(`${base}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      signal: AbortSignal.timeout(_TIMEOUT_MS),
    });
  } catch (err) {
    throw new ApiError(_mensagemDeFalha(err));
  }
  if (resp.status === 401) throw new ApiError("Sessão expirada. Faça login novamente.", 401);
  if (!resp.ok) throw new ApiError(`Falha ao renovar sessão (HTTP ${resp.status}).`, resp.status);
  const body = await resp.json();
  return body.access_token;
}

// 401 tenta renovar o token uma vez antes de desistir.
export async function authedGet(apiPath) {
  const tokens = loadTokens();
  if (!tokens) throw new ApiError("Não autenticado. Rode `cronista login`.", 401);

  let resp = await request("GET", apiPath, tokens.accessToken);
  if (resp.status === 401) {
    const newAccessToken = await refresh(tokens.refreshToken);
    saveTokens(newAccessToken, tokens.refreshToken);
    resp = await request("GET", apiPath, newAccessToken);
  }
  if (!resp.ok) throw new ApiError(`Erro na API (HTTP ${resp.status}).`, resp.status);
  return resp.json();
}

export function listMeetings() {
  return authedGet("/meetings");
}

export function getMeeting(meetingId) {
  return authedGet(`/meetings/${meetingId}`);
}

export function getTranscript(meetingId) {
  return authedGet(`/meetings/${meetingId}/transcript`);
}

export function search(q) {
  return authedGet(`/search?${new URLSearchParams({ q }).toString()}`);
}
