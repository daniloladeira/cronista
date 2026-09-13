import React from "react";
import { Box, Text } from "ink";

const h = React.createElement;
const PADRAO_WIDTH = 6;

// minWidth: 0 é necessário -- sem ele, Yoga não deixa o item flexível
// encolher abaixo do tamanho do próprio texto, e a truncagem não funciona.
function Row({ left, right, bold }) {
  return h(
    Box,
    null,
    h(Box, { flexGrow: 1, minWidth: 0 }, h(Text, { bold, wrap: "truncate-end" }, left)),
    h(Box, { width: PADRAO_WIDTH, flexShrink: 0, justifyContent: "flex-end" }, h(Text, { bold }, right))
  );
}

export default function DeviceTable({ devices }) {
  return h(
    Box,
    { flexDirection: "column" },
    h(Row, { key: "header", left: "Nome", right: "Padrão", bold: true }),
    ...devices.map((d, i) => h(Row, { key: i, left: d.name, right: d.is_default ? "sim" : "" }))
  );
}
