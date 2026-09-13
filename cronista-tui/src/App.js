import React, { useState } from "react";
import { Box, Text, useApp, useInput, useStdout, useWindowSize } from "ink";
import Home from "./screens/Home.js";
import Header from "./screens/Header.js";
import Sidebar, { ITEMS, SIDEBAR_WIDTH } from "./screens/Sidebar.js";
import Devices from "./screens/Devices.js";
import Meetings from "./screens/Meetings.js";
import Footer, { footerHints, ConfirmQuit } from "./screens/Footer.js";
import Spinner from "./Spinner.js";
import { runPythonCaptured } from "./pythonBridge.js";
import { DOURADO, NEUTRO, ERRO } from "./theme.js";

// "sync" não precisa do terminal inteiro (sem prompt, sem áudio) -- roda em
// paralelo ao Ink, sem sair. Os outros launchers (rec, login) continuam
// saindo: um precisa do terminal pra captura de áudio, o outro pede senha.
const _INLINE_SUBS = new Set(["sync"]);

const h = React.createElement;

// Exportadas pro capture.js compor a mesma tela em vez de duplicar a
// fórmula -- foi exatamente essa duplicação que deixou capture.js preso
// no teto de largura antigo enquanto este arquivo já tinha mudado.
//
// Sem teto: o painel preenche o terminal inteiro (torlink Results.tsx
// não limita largura nenhuma -- o teto de 90 daqui era emprestado por
// engano do prompt centralizado de Home.js, que é um caso diferente).
export function contentWidth(columns) {
  return Math.max(30, columns - 4 - SIDEBAR_WIDTH);
}

// Linhas fixas da "moldura" fora do corpo: Header (título + régua) = 2,
// margem antes do corpo = 1, margem antes do rodapé + o rodapé = 2.
// Espelha bodyH de App.tsx do torlink (rows - 1 - chrome).
const _CHROME_ROWS = 5;
export function bodyHeight(rows) {
  return Math.max(6, rows - _CHROME_ROWS);
}

// A linha de título do Panel (desenhada à mão, fora da box com border)
// come 1 das bodyHeight linhas reservadas pro corpo -- sem isto o painel
// extrapolava por 1 linha (Panel.js title + inner box). Exportada pelo
// mesmo motivo de contentWidth/bodyHeight -- capture.js reimplementava
// esta mesma conta à parte, achado revisando o código.
export function panelHeight(rows) {
  return Math.max(4, bodyHeight(rows) - 1);
}

function renderInlineResult(inlineResult) {
  if (inlineResult === null) {
    return h(Text, { dimColor: true }, "↵ roda agora, sem sair daqui");
  }
  if (inlineResult === "running") {
    return h(Box, null, h(Spinner, { color: DOURADO }), h(Text, null, " sincronizando..."));
  }
  return h(
    Box,
    { flexDirection: "column" },
    ...inlineResult.lines.map((line, i) => h(Text, { key: i, color: inlineResult.ok ? NEUTRO : ERRO }, line))
  );
}

// initialSection/initialMeetingId/initialSearchTerm são prop, não
// constante de módulo -- index.js monta este componente mais de uma vez
// no mesmo processo, cada vez com um valor inicial diferente.
export default function App({ onLaunch, onClearScreen, initialSection = null, initialMeetingId = null, initialSearchTerm = null }) {
  const { exit } = useApp();
  const { stdout } = useStdout();

  // useWindowSize (Ink 7+, nativo) -- re-renderiza sozinho quando o
  // terminal redimensiona, coordenado com o próprio ciclo de render do
  // Ink. Testei sem NENHUM acompanhamento de resize (nem isto nem a
  // versão manual anterior) isolando a causa do flicker: continuava
  // piscando -- não era isto, era o Ink desenhando fora da tela
  // alternativa (ver index.js, `alternateScreen: true`).
  const { columns: liveColumns, rows: liveRows } = useWindowSize();
  const columns = liveColumns || 80;
  const rows = liveRows || 24;

  const [initialItem] = useState(() => ITEMS.find((i) => i.key === initialSection) || ITEMS[0]);
  const [view, setView] = useState(initialSection ? "main" : "home"); // 'home' | 'main'
  const [cursorItem, setCursorItem] = useState(initialItem);
  const [section, setSection] = useState(initialItem.kind === "section" ? initialItem.key : "reunioes");
  const [region, setRegion] = useState(initialSection ? "content" : "sidebar"); // 'sidebar' | 'content'
  // null | "running" | { ok, lines } -- só usado pelos subs de _INLINE_SUBS.
  const [inlineResult, setInlineResult] = useState(null);
  const [confirmingQuit, setConfirmingQuit] = useState(false);
  // TTY checada uma vez aqui, propagada em todo `focused` -- sem terminal
  // de verdade, o Ink não pode ligar modo raw.
  const interactive = Boolean(stdout.isTTY);

  // Escape não tem handler global: cada tela decide se é dela (detalhe →
  // lista) ou se sobra pro nível de cima (lista → sidebar → home).
  function goHome() {
    onClearScreen?.();
    setView("home");
  }

  function goMain() {
    onClearScreen?.();
    setView("main");
  }

  useInput(
    (input, key) => {
      if (confirmingQuit) {
        // Só "q" confirma, igual o texto na tela diz -- Enter também
        // confirmando contradizia "qualquer outra tecla cancela".
        if (input === "q") exit();
        else setConfirmingQuit(false);
        return;
      }
      if (input === "q") {
        setConfirmingQuit(true);
        return;
      }
      if (view === "home" && key.return) goMain();
    },
    { isActive: Boolean(stdout.isTTY) }
  );

  if (view === "home") {
    return h(Home, { confirmingQuit });
  }

  const w = contentWidth(columns);

  function onChangeCursor(item) {
    if (item.key !== cursorItem.key) setInlineResult(null);
    setCursorItem(item);
    if (item.kind === "section") setSection(item.key);
  }

  async function runInline(sub) {
    setInlineResult("running");
    const result = await runPythonCaptured(sub);
    const lines = [...result.stdout.split("\n"), ...result.stderr.split("\n")].filter(Boolean);
    if (lines.length === 0) lines.push("Nada pendente.");
    setInlineResult({ ok: result.code === 0 && result.stderr === "", lines });
  }

  function onLaunchItem(item) {
    if (_INLINE_SUBS.has(item.sub)) {
      if (inlineResult === "running") return; // já rodando, ignora novo Enter
      runInline(item.sub);
      return;
    }
    onLaunch?.(item.sub, section);
    exit();
  }

  const bh = bodyHeight(rows);
  const panelH = panelHeight(rows);

  const content =
    cursorItem.kind === "launch"
      ? h(
          Box,
          { flexDirection: "column" },
          h(Text, { dimColor: true }, cursorItem.hint),
          h(
            Box,
            { marginTop: 1 },
            _INLINE_SUBS.has(cursorItem.sub)
              ? renderInlineResult(inlineResult)
              : h(Text, { dimColor: true }, "↵ roda agora, sai do cronista-tui")
          )
        )
      : section === "reunioes"
        ? h(Meetings, {
            width: w,
            height: panelH,
            focused: interactive && region === "content",
            onBack: () => setRegion("sidebar"),
            initialMeetingId,
            initialSearchTerm,
          })
        : h(Devices, { width: w, focused: interactive && region === "content", onBack: () => setRegion("sidebar") });

  return h(
    Box,
    { flexDirection: "column", paddingX: 2 },
    h(Header, { width: Math.max(10, columns - 4) }),
    h(
      Box,
      { marginTop: 1, height: bh, overflow: "hidden" },
      h(Sidebar, {
        cursorKey: cursorItem.key,
        onChangeCursor,
        focused: interactive && region === "sidebar",
        onEnter: () => setRegion("content"),
        onBack: goHome,
        onLaunch: onLaunchItem,
      }),
      content
    ),
    h(Box, { marginTop: 1 }, confirmingQuit ? h(ConfirmQuit) : h(Footer, { hints: footerHints(region) }))
  );
}
