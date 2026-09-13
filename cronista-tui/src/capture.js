// Captura estática, sem TTY -- useInput fica inativo, então aqui a
// "seção" e a "view" são fixadas na composição em vez de navegadas por tecla.
import React from "react";
import { render } from "ink-testing-library";
import { Box, Text } from "ink";
import stripAnsi from "strip-ansi";
import Home from "./screens/Home.js";
import Header from "./screens/Header.js";
import Sidebar from "./screens/Sidebar.js";
import Devices from "./screens/Devices.js";
import Meetings from "./screens/Meetings.js";
import MeetingDetail from "./MeetingDetail.js";
import TextInput from "./TextInput.js";
import Footer, { footerHints } from "./screens/Footer.js";
import { contentWidth, bodyHeight, panelHeight } from "./App.js";

const h = React.createElement;

// Espelha o retorno de App.js pra "main" -- reusa contentWidth/bodyHeight/
// panelHeight de lá em vez de recalcular, pra não desalinhar de novo (ver App.js).
function MainView({ columns, rows = 24, section }) {
  const w = contentWidth(columns);
  const bh = bodyHeight(rows);
  const panelH = panelHeight(rows);
  return h(
    Box,
    { flexDirection: "column", paddingX: 2 },
    h(Header, { width: Math.max(10, columns - 4) }),
    h(
      Box,
      { marginTop: 1, height: bh, overflow: "hidden" },
      h(Sidebar, {
        cursorKey: section,
        onChangeCursor: () => {},
        focused: section === "reunioes",
        onEnter: () => {},
        onBack: () => {},
        onLaunch: () => {},
      }),
      section === "reunioes"
        ? h(Meetings, { width: w, height: panelH, focused: true, onBack: () => {} })
        : h(Devices, { width: w, focused: true, onBack: () => {} })
    ),
    h(Box, { marginTop: 1 }, h(Footer, { hints: footerHints("content") }))
  );
}

async function snapshot(label, node) {
  console.log(`\n########## ${label} ##########`);
  const { lastFrame, unmount } = render(node);
  await new Promise((r) => setTimeout(r, 3000)); // Devices/Meetings resolvem async
  console.log(stripAnsi(lastFrame()));
  unmount();
}

for (const columns of [100, 60]) {
  await snapshot(`home, ${columns} colunas`, h(Home));
}
await snapshot("main / dispositivos, 100x30", h(MainView, { columns: 100, rows: 30, section: "dispositivos" }));
await snapshot(
  "main / reuniões, 100x30 (API real esperada fora do ar nesta máquina agora)",
  h(MainView, { columns: 100, rows: 30, section: "reunioes" })
);

// Dado sintético só pra conferir layout.
const reuniaoFalsa = {
  id: "fake-1",
  title: "Reunião de alinhamento — sprint 12",
  summaries: [
    {
      generated_at: "2026-09-01T10:00:00Z",
      markdown: "## Pauta\n- Item 1\n- Item 2\n\n## Decisões\n- Decidido X\n\n## Pendências\n- Fulano faz Y",
    },
  ],
};
const segmentosFalsos = Array.from({ length: 20 }, (_, i) => ({
  timestamp: `00:0${i % 6}:00`,
  speaker: i % 2 === 0 ? "voce" : "outros",
  text: `Linha de transcrição sintética número ${i + 1}, só pra testar rolagem.`,
}));

await snapshot(
  "MeetingDetail (dado sintético), aba transcrição",
  h(MeetingDetail, { meeting: reuniaoFalsa, segments: segmentosFalsos, width: 80, focused: true, onBack: () => {} })
);

await snapshot(
  "Meetings em modo busca (TextInput)",
  h(TextInput, { value: "decisão", onChange: () => {}, onSubmit: () => {}, onCancel: () => {}, placeholder: "Buscar…", focused: false })
);

function SidebarComLaunch({ cursorKey }) {
  const w = contentWidth(100);
  return h(
    Box,
    { flexDirection: "column", paddingX: 2 },
    h(Header, { width: 96 }),
    h(
      Box,
      { marginTop: 1 },
      h(Sidebar, { cursorKey, onChangeCursor: () => {}, focused: true, onEnter: () => {}, onBack: () => {}, onLaunch: () => {} }),
      h(Box, { flexDirection: "column", width: w }, h(Text, { dimColor: true }, "cronista rec -- grava até Ctrl+C, sai do Ink"))
    )
  );
}
await snapshot("sidebar com lançadores, cursor em Gravar", h(SidebarComLaunch, { cursorKey: "gravar" }));
