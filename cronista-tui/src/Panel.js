import React from "react";
import { Box, Text } from "ink";

const h = React.createElement;

// Ink não tem título nativo de borda -- a linha de cima é desenhada à
// mão, o resto (`borderStyle="round" borderTop={false}`) é Box real.
export default function Panel({ title, color, width, height, children }) {
  const w = Math.max(10, width);
  // "╭─ " (3) + title + " " + fill traços + "╮" (2) = title.length + fill + 5.
  const fill = Math.max(0, w - title.length - 5);

  return h(
    Box,
    { flexDirection: "column", width: w },
    h(
      Box,
      null,
      h(Text, { color }, "╭─ "),
      h(Text, { color, bold: true }, title),
      h(Text, { color }, ` ${"─".repeat(fill)}╮`)
    ),
    h(
      Box,
      {
        width: w,
        // Número explícito, não flexGrow (torlink Panel.tsx: height={panelH}):
        // o Box deste painel não é esticado pelo pai (é filho de um Box
        // column, sem stretch de altura no eixo principal), então flexGrow
        // sozinho aqui não tinha altura nenhuma pra preencher -- só um
        // height concreto, calculado lá em cima (App.js: bodyHeight), funciona.
        height,
        flexDirection: "column",
        borderStyle: "round",
        borderTop: false,
        borderColor: color,
        paddingX: 1,
        overflow: "hidden",
      },
      children
    )
  );
}
