import React from "react";
import { Box, Text } from "ink";
import { NEUTRO } from "./theme.js";

const h = React.createElement;
export const VIEWPORT_HEIGHT = 14;

// Ink não tem painel com scroll nativo -- janela manual: mostra só
// VIEWPORT_HEIGHT linhas a partir de offset.
export default function ScrollText({ lines, offset }) {
  if (lines.length === 0) {
    return h(Text, { dimColor: true }, "(vazio)");
  }
  const visible = lines.slice(offset, offset + VIEWPORT_HEIGHT);
  return h(
    Box,
    { flexDirection: "column" },
    ...visible.map((line, i) => h(Text, { key: offset + i, wrap: "truncate-end" }, line)),
    lines.length > VIEWPORT_HEIGHT
      ? h(
          Box,
          { marginTop: 1 },
          h(Text, { color: NEUTRO, dimColor: true }, `${offset + 1}-${Math.min(offset + VIEWPORT_HEIGHT, lines.length)} de ${lines.length} · ↑↓ rolar`)
        )
      : null
  );
}

export function clampOffset(offset, totalLines) {
  return Math.max(0, Math.min(offset, Math.max(0, totalLines - VIEWPORT_HEIGHT)));
}
