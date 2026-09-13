import React from "react";
import { Box, Text } from "ink";
import figlet from "figlet";
import { lerpColor } from "./shimmer.js";
import { DOURADO } from "./theme.js";

const h = React.createElement;

// Degradê por CARACTERE numa grade 2D (linha e coluna combinadas), não
// por letra -- dá o efeito de luz vindo de um canto.
const FONT = "ANSI Compact";
const HIGHLIGHT = "#FFFFFF";
const TOP = "#F7ECDA";
const ACCENT = DOURADO; // #DFB878
const BASE = "#C9A968";
const SHADE = "#B8934F"; // ponto mais escuro do degradê -- ainda dourado, nunca marrom apagado

function sheen(t) {
  if (t < 0.15) return lerpColor(HIGHLIGHT, TOP, t / 0.15);
  if (t < 0.4) return lerpColor(TOP, ACCENT, (t - 0.15) / 0.25);
  if (t < 0.7) return lerpColor(ACCENT, BASE, (t - 0.4) / 0.3);
  return lerpColor(BASE, SHADE, (t - 0.7) / 0.3);
}

export function bannerRows(word) {
  return figlet.textSync(word, { font: FONT }).split("\n").filter((row) => row.trim() !== "");
}

export function bannerWidth(word) {
  return Math.max(...bannerRows(word).map((row) => Array.from(row).length));
}

// Estático -- sem sweep/shimmer, isso é só do cabeçalho pequeno.
export default function Banner({ word = "cronista" }) {
  const rows = bannerRows(word);
  const nRows = rows.length;
  const nCols = Math.max(...rows.map((row) => Array.from(row).length));

  return h(
    Box,
    // width: nCols é obrigatório nas duas pontas (aqui e por linha,
    // embaixo) -- espaço em branco no FIM de uma linha, sem nada depois,
    // some da largura que o Ink mede sozinho, e as linhas desalinhariam.
    { flexDirection: "column", width: nCols },
    ...rows.map((row, rowIdx) => {
      const tY = rowIdx / Math.max(1, nRows - 1);
      const chars = Array.from(row);
      return h(
        Box,
        { key: rowIdx, width: nCols },
        ...chars.map((ch, colIdx) => {
          if (ch === " ") return h(Text, { key: colIdx }, " ");
          const tX = colIdx / Math.max(1, nCols - 1);
          return h(Text, { key: colIdx, bold: true, color: sheen((tX + tY) / 2) }, ch);
        })
      );
    })
  );
}
