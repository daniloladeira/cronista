import React from "react";
import { Box, Text } from "ink";
import { DOURADO } from "./theme.js";

const h = React.createElement;

// Status vem cru da API (cronista/core/models.py) -- sem tradução, a
// lista misturava pt-BR com termo técnico em inglês no meio da frase.
const _STATUS_LABEL = {
  registering: "registrando",
  recorded: "gravada",
  transcribing: "transcrevendo",
  transcribed: "transcrita",
  summarized: "resumida",
  transcription_failed: "falha na transcrição",
  summary_failed: "falha no resumo",
};

function rotulo(reuniao) {
  return `${reuniao.title} · ${_STATUS_LABEL[reuniao.status] || reuniao.status}`;
}

export default function MeetingList({ meetings, cursor, focused }) {
  if (meetings.length === 0) {
    return h(Text, { color: "#666666" }, "Nenhuma reunião encontrada.");
  }
  return h(
    Box,
    { flexDirection: "column" },
    ...meetings.map((m, i) => {
      const selected = i === cursor;
      return h(
        Box,
        { key: m.id },
        h(Box, { width: 2, flexShrink: 0 }, selected ? h(Text, { color: DOURADO, bold: focused }, "❯ ") : null),
        h(
          Box,
          { flexGrow: 1, minWidth: 0 },
          h(
            Text,
            {
              wrap: "truncate-end",
              color: selected ? (focused ? DOURADO : undefined) : undefined,
              dimColor: !selected,
              bold: selected && focused,
            },
            rotulo(m)
          )
        )
      );
    })
  );
}
