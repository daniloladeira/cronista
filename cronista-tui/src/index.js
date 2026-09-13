import React from "react";
import { render } from "ink";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import App from "./App.js";
import { launchPython } from "./pythonBridge.js";

const __filename = fileURLToPath(import.meta.url);

// Node controlando o stdin ele mesmo (readline, raw mode, ou outro
// render() do Ink) derruba o processo depois que um filho Python usou o
// mesmo stdio herdado -- só um comando nativo do cmd.exe (não Node lendo
// stdin) resolvia isso de verdade. TESTE: `timeout /nobreak` troca
// "aperte uma tecla" por uma espera curta sem tecla nenhuma, mas
// continua nativo do cmd.exe (mesma característica que resolvia o
// problema original) -- se ainda quebrar rec/login, volta pro `pause`.
function pauseForKey() {
  process.stdout.write("\n");
  spawnSync("cmd.exe", ["/c", "timeout", "/t", "2", "/nobreak"], { stdio: "inherit" });
}

let requested = null;
let requestedSection = null;
const instance = render(
  React.createElement(App, {
    onLaunch: (sub, section) => {
      requested = sub;
      requestedSection = section;
    },
    onClearScreen: () => instance.clear(),
    initialSection: process.env.CRONISTA_TUI_SECTION || null,
    initialMeetingId: process.env.CRONISTA_TUI_MEETING_ID || null,
    initialSearchTerm: process.env.CRONISTA_TUI_SEARCH_TERM || null,
  }),
  // Tela alternativa do terminal (Ink 7+, nativo) -- mesmo mecanismo de
  // vim/htop/less, e do torlink (mas eles fazem na mão, com código ANSI
  // cru, porque escreveram isso antes dessa opção existir no Ink). Sem
  // isto, o Ink reescreve a tela por cima da tela normal/scrollback; um
  // redimensionamento ao vivo faz as duas coisas brigarem pelo mesmo
  // espaço ao mesmo tempo -- é isso que causava o flicker (achado
  // comparando contra o torlink). Ink cuida sozinho de sair da tela
  // alternativa ao desmontar, inclusive em crash -- não precisa mais de
  // ANSI na mão nem de `process.on("exit", ...)`.
  { alternateScreen: true }
);

await instance.waitUntilExit();

if (requested) {
  // O import do cli.py sozinho custa ~600ms (numpy/soundcard/typer/rich),
  // antes de qualquer linha de `rec`/`login` rodar -- sem isto, esse
  // tempo aparecia como o prompt do PowerShell de antes parado na tela,
  // como se tivesse voltado sozinho (achado revisando com o usuário, não
  // presumido). Não dá pra zerar o custo sem mexer nos imports do
  // Python; dá pra não deixar a espera parecer que não está acontecendo
  // nada.
  process.stdout.write(`\nIniciando cronista ${requested}...\n`);
  const resultado = launchPython(requested);
  if (resultado.error) {
    process.stdout.write(`\nErro: não consegui rodar "cronista ${requested}" (${resultado.error.message}).\n`);
  }
  pauseForKey();
  // Volta pra seção de onde saiu (Dispositivos, Reuniões...), não sempre
  // Reuniões -- section vem do estado do App no momento do lançamento.
  spawnSync(process.execPath, [__filename], {
    stdio: "inherit",
    env: {
      ...process.env,
      CRONISTA_TUI_SECTION: requestedSection || "reunioes",
      CRONISTA_TUI_MEETING_ID: "",
      CRONISTA_TUI_SEARCH_TERM: "",
    },
  });
}
