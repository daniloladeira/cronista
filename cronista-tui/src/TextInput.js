import React from "react";
import { Box, Text, useInput, usePaste } from "ink";
import { DOURADO } from "./theme.js";

const h = React.createElement;

export default function TextInput({ value, onChange, onSubmit, onCancel, placeholder = "", focused }) {
  useInput(
    (input, key) => {
      if (key.return) {
        onSubmit(value);
        return;
      }
      if (key.escape) {
        onCancel();
        return;
      }
      if (key.backspace || key.delete) {
        onChange(value.slice(0, -1));
        return;
      }
      // key.ctrl/meta filtra atalho (ctrl+c etc.) pra não virar texto
      if (input && !key.ctrl && !key.meta) {
        onChange(value + input);
      }
    },
    { isActive: focused }
  );

  // Canal separado do useInput acima (Ink 7+) -- sem isto, colar um
  // termo de busca chegava como uma tecla por caractere, indistinguível
  // de digitar rápido. Campo de uma linha só: quebra de linha do que foi
  // colado vira espaço, não insere newline de verdade no valor.
  usePaste(
    (text) => onChange(value + text.replace(/\r\n|\r|\n/g, " ")),
    { isActive: focused }
  );

  return h(
    Box,
    null,
    h(Text, { color: DOURADO }, "/ "),
    value ? h(Text, null, value) : h(Text, { dimColor: true }, placeholder),
    h(Text, { color: DOURADO }, "▏")
  );
}
