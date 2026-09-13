import React from "react";
import { Box, Text, useInput } from "ink";
import { DOURADO, NEUTRO } from "../theme.js";

const h = React.createElement;

// "section": tela persistente dentro do próprio Ink. "launch": sai do
// Ink e roda `cronista <sub>` (Python) com o terminal inteiro pra ele.
export const SECTIONS = [
  { key: "reunioes", label: "Reuniões", kind: "section" },
  { key: "dispositivos", label: "Dispositivos", kind: "section" },
];
export const LAUNCHERS = [
  { key: "gravar", label: "Gravar", kind: "launch", sub: "rec", hint: "cronista rec -- grava até Ctrl+C, sai do Ink" },
  { key: "sincronizar", label: "Sincronizar", kind: "launch", sub: "sync", hint: "cronista sync -- reenvia reuniões pendentes" },
  { key: "login", label: "Login", kind: "launch", sub: "login", hint: "cronista login -- pede usuário/senha" },
];
export const ITEMS = [...SECTIONS, ...LAUNCHERS];
const GROUPS = [SECTIONS, LAUNCHERS];

const _INDICATOR_WIDTH = 2;
const _MARGIN_RIGHT = 4;
const _INNER_WIDTH = _INDICATOR_WIDTH + Math.max(...ITEMS.map((i) => i.label.length));
// Rodapé horizontal TOTAL (largura própria + margem) -- App.js/capture.js
// precisam contar os dois pra largura do conteúdo ao lado bater certo.
export const SIDEBAR_WIDTH = _INNER_WIDTH + _MARGIN_RIGHT;

export default function Sidebar({ cursorKey, onChangeCursor, focused, onEnter, onBack, onLaunch }) {
  const idx = Math.max(0, ITEMS.findIndex((i) => i.key === cursorKey));

  useInput(
    (input, key) => {
      if (key.upArrow || input === "k") {
        onChangeCursor(ITEMS[(idx - 1 + ITEMS.length) % ITEMS.length]);
      } else if (key.downArrow || input === "j") {
        onChangeCursor(ITEMS[(idx + 1) % ITEMS.length]);
      } else if (key.return || key.rightArrow) {
        const item = ITEMS[idx];
        if (item.kind === "launch") onLaunch(item);
        else onEnter();
      } else if (key.escape || key.leftArrow) {
        onBack();
      }
    },
    { isActive: focused }
  );

  return h(
    Box,
    { flexDirection: "column", width: _INNER_WIDTH, flexShrink: 0, marginRight: _MARGIN_RIGHT },
    ...GROUPS.map((group, gi) =>
      h(
        Box,
        { key: gi, flexDirection: "column", marginTop: gi > 0 ? 1 : 0 },
        ...group.map((item) => {
          const selected = item.key === cursorKey;
          return h(
            Box,
            { key: item.key },
            h(Box, { width: 2, flexShrink: 0 }, selected ? h(Text, { color: focused ? DOURADO : NEUTRO, bold: focused }, "❯ ") : null),
            h(
              Text,
              {
                color: selected ? (focused ? DOURADO : undefined) : undefined,
                dimColor: !selected,
                bold: selected && focused,
              },
              item.label
            )
          );
        })
      )
    )
  );
}
