import React from "react";
import { Box, Text } from "ink";
import { DOURADO, ERRO, NEUTRO } from "../theme.js";

const h = React.createElement;

// Uma Text só, aninhada (não Box) -- wrap="truncate-end" só funciona
// assim: com Box por hint, terminal estreito quebraria em várias linhas
// em vez de truncar (mesma técnica de Footer.tsx do torlink).
export default function Footer({ hints }) {
  return h(
    Box,
    null,
    h(
      Text,
      { wrap: "truncate-end" },
      ...hints.map((hint, i) =>
        h(
          Text,
          { key: hint.keys + hint.label },
          i > 0 ? h(Text, { color: NEUTRO }, "   ") : null,
          h(Text, { color: DOURADO }, hint.keys),
          h(Text, { color: NEUTRO }, ` ${hint.label}`)
        )
      )
    )
  );
}

export function ConfirmQuit() {
  return h(
    Box,
    null,
    h(Text, { color: ERRO }, "sair? ", h(Text, { bold: true }, "q"), " confirma · qualquer outra tecla cancela")
  );
}

export function footerHints(region) {
  return region === "sidebar"
    ? [
        { keys: "↑↓", label: "mover" },
        { keys: "↵/→", label: "abrir" },
        { keys: "q", label: "sair" },
      ]
    : [
        { keys: "↑↓", label: "mover" },
        { keys: "↵", label: "abrir" },
        { keys: "←/Esc", label: "voltar" },
        { keys: "q", label: "sair" },
      ];
}
