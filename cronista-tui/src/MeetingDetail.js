import React, { useState } from "react";
import { Box, Text, useInput } from "ink";
import Panel from "./Panel.js";
import ScrollText, { clampOffset, VIEWPORT_HEIGHT } from "./ScrollText.js";
import { DOURADO } from "./theme.js";

const h = React.createElement;

const TABS = [
  { key: "transcricao", label: "Transcrição" },
  { key: "resumo", label: "Resumo" },
];

function transcriptLines(segments) {
  if (!segments || segments.length === 0) return ["(sem transcrição ainda)"];
  return segments.map((s) => `[${s.timestamp}] ${s.speaker}: ${s.text}`);
}

// Resumo mais recente por generated_at. Texto puro, sem estilo markdown.
function latestSummaryLines(meeting) {
  const summaries = meeting.summaries || [];
  if (summaries.length === 0) return ["(sem resumo ainda)"];
  const latest = [...summaries].sort((a, b) => a.generated_at.localeCompare(b.generated_at)).at(-1);
  return latest.markdown.split("\n");
}

// onBack só é chamado quando já não há mais nível pra descer (a tela
// devolve o foco pra Meetings.js, não direto pra sidebar).
export default function MeetingDetail({ meeting, segments, width, height, focused, onBack }) {
  const [tab, setTab] = useState("transcricao");
  const [offsets, setOffsets] = useState({ transcricao: 0, resumo: 0 });

  const lines = tab === "transcricao" ? transcriptLines(segments) : latestSummaryLines(meeting);
  const offset = offsets[tab];

  useInput(
    (input, key) => {
      if (key.escape || key.leftArrow) {
        onBack();
        return;
      }
      if (key.tab) {
        setTab((t) => (t === "transcricao" ? "resumo" : "transcricao"));
        return;
      }
      if (key.upArrow || input === "k") setOffsets((o) => ({ ...o, [tab]: clampOffset(o[tab] - 1, lines.length) }));
      else if (key.downArrow || input === "j")
        setOffsets((o) => ({ ...o, [tab]: clampOffset(o[tab] + 1, lines.length) }));
      else if (key.pageUp) setOffsets((o) => ({ ...o, [tab]: clampOffset(o[tab] - VIEWPORT_HEIGHT, lines.length) }));
      else if (key.pageDown)
        setOffsets((o) => ({ ...o, [tab]: clampOffset(o[tab] + VIEWPORT_HEIGHT, lines.length) }));
    },
    { isActive: focused }
  );

  return h(
    Panel,
    { title: meeting.title, color: DOURADO, width, height },
    h(
      Box,
      { marginBottom: 1 },
      ...TABS.map((t) =>
        h(
          Box,
          { key: t.key, marginRight: 2 },
          h(Text, { color: t.key === tab ? DOURADO : undefined, bold: t.key === tab, dimColor: t.key !== tab }, t.label)
        )
      )
    ),
    h(ScrollText, { lines, offset }),
    h(Box, { marginTop: 1 }, h(Text, { dimColor: true }, "Tab troca aba · ↑↓ rola · Esc volta"))
  );
}
