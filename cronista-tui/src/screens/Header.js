import React, { useEffect, useState } from "react";
import { Box, Text } from "ink";
import Rule from "../Rule.js";
import { shimmerChars, shimmerPosition } from "../shimmer.js";
import { DOURADO, FLASH_COLOR, FLASH_WIDTH, SWEEP_SECONDS, PAUSE_BETWEEN_SWEEPS, FRAME_MS, BANNER_WORD } from "../constants.js";

const h = React.createElement;

export default function Header({ width }) {
  const [startedAt] = useState(() => Date.now());
  const [position, setPosition] = useState(() =>
    shimmerPosition(Date.now(), BANNER_WORD.length, FLASH_WIDTH, SWEEP_SECONDS, PAUSE_BETWEEN_SWEEPS)
  );

  useEffect(() => {
    const id = setInterval(() => {
      const next = shimmerPosition(startedAt, BANNER_WORD.length, FLASH_WIDTH, SWEEP_SECONDS, PAUSE_BETWEEN_SWEEPS);
      // Ink redesenha a TELA INTEIRA a cada commit de estado, não só o
      // Header -- fora da varredura, a posição fica parada em -999 (ver
      // shimmer.js) e chamar setState com o mesmo valor de novo e de
      // novo forçava ~13 redesenhos/s à toa (achado revisando o código,
      // não presumido: confirmado lendo node_modules/ink/build/ink.js,
      // onRender serializa a árvore inteira em todo commit). React já
      // pula o re-render quando o setter devolve o mesmo valor (Object.is).
      setPosition((prev) => (prev === next ? prev : next));
    }, FRAME_MS);
    return () => clearInterval(id);
  }, [startedAt]);

  const chars = shimmerChars(BANNER_WORD, position, DOURADO, FLASH_COLOR, FLASH_WIDTH);

  return h(
    Box,
    { flexDirection: "column" },
    h(Box, null, ...chars.map((c, i) => h(Text, { key: i, bold: true, color: c.color }, c.ch))),
    h(Rule, { width, color: DOURADO })
  );
}
