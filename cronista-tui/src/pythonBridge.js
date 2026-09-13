import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.join(__dirname, "..", "..");
const CRONISTA_EXE = path.join(REPO_ROOT, ".venv", "Scripts", "cronista.exe");

// Só seguro chamar depois do Ink desmontar (ver index.js) -- os dois
// processos disputando o modo raw do mesmo stdin corrompe o terminal.
//
// Devolve o resultado (não descarta): `.error` vem preenchido se o
// processo nem chegou a iniciar (ex.: .venv/Scripts/cronista.exe
// ausente) -- sem checar isso, index.js seguia pro "pressione tecla"
// como se `cronista rec`/`login` tivesse rodado de verdade.
export function launchPython(sub) {
  return spawnSync(CRONISTA_EXE, [sub], { stdio: "inherit" });
}

// Pra sub-comandos sem interação (sync): roda em paralelo ao Ink, sem
// herdar stdio -- o resultado vira estado de React, não uma tela nova.
export function runPythonCaptured(sub) {
  return new Promise((resolve) => {
    const child = spawn(CRONISTA_EXE, [sub], {
      stdio: ["ignore", "pipe", "pipe"],
      // Sem console real herdado, o Python no Windows cai pro codepage
      // legado (cp1252) e o pipe vira bytes inválidos em UTF-8 -- achado
      // rodando de verdade ("reuni�o" em vez de "reunião"), não presumido.
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    // Sem isto, cronista.exe ausente/sem permissão nunca emite "close" --
    // a Promise fica pendurada pra sempre e o spinner de sincronizar
    // gira infinito, sem erro nenhum (achado revisando, não presumido).
    child.on("error", (err) => resolve({ code: null, stdout: "", stderr: String(err) }));
    child.on("close", (code) => resolve({ code, stdout: stdout.trim(), stderr: stderr.trim() }));
  });
}
