import React, { useEffect, useState } from "react";
import { Box, Text, useStdout } from "ink";
import Banner, { bannerWidth } from "../Banner.js";
import { shimmerChars, shimmerPosition } from "../shimmer.js";
import { DOURADO, FLASH_COLOR, FLASH_WIDTH, SWEEP_SECONDS, PAUSE_BETWEEN_SWEEPS, FRAME_MS, BANNER_WORD } from "../constants.js";
import { ERRO } from "../theme.js";

const h = React.createElement;

const BIG_BANNER_WIDTH = bannerWidth(BANNER_WORD);

// Fallback quando o terminal não cabe o banner grande.
function SmallShimmerTitle() {
  const [startedAt] = useState(() => Date.now());
  const [position, setPosition] = useState(() =>
    shimmerPosition(Date.now(), BANNER_WORD.length, FLASH_WIDTH, SWEEP_SECONDS, PAUSE_BETWEEN_SWEEPS)
  );

  useEffect(() => {
    const id = setInterval(() => {
      const next = shimmerPosition(startedAt, BANNER_WORD.length, FLASH_WIDTH, SWEEP_SECONDS, PAUSE_BETWEEN_SWEEPS);
      // Mesmo motivo de screens/Header.js: fora da varredura a posição
      // fica parada, e setState com o mesmo valor não força redesenho.
      setPosition((prev) => (prev === next ? prev : next));
    }, FRAME_MS);
    return () => clearInterval(id);
  }, [startedAt]);

  const chars = shimmerChars(BANNER_WORD, position, DOURADO, FLASH_COLOR, FLASH_WIDTH);
  return h(Box, null, ...chars.map((c, i) => h(Text, { key: i, bold: true, color: c.color }, c.ch)));
}

export default function Home({ confirmingQuit = false }) {
  const { stdout } = useStdout();
  const rows = stdout.rows || 24;
  const columns = stdout.columns || 80;
  const big = columns >= BIG_BANNER_WIDTH + 2;

  return h(
    Box,
    { height: Math.max(1, rows - 1), flexDirection: "column", justifyContent: "center", alignItems: "center" },
    big ? h(Banner, { word: BANNER_WORD }) : h(SmallShimmerTitle),
    h(Box, { marginTop: 1 }, h(Text, { color: "#888888" }, "Grava, transcreve e resume reuniões, localmente.")),
    h(
      Box,
      { marginTop: 2 },
      confirmingQuit
        ? h(Text, { color: ERRO }, "sair? ", h(Text, { bold: true }, "q"), " confirma · qualquer outra tecla cancela")
        : h(
            Text,
            null,
            h(Text, null, h(Text, { color: DOURADO }, "↵"), h(Text, { dimColor: true }, " abrir menu")),
            h(Text, { dimColor: true }, "   "),
            h(Text, null, h(Text, { color: DOURADO }, "q"), h(Text, { dimColor: true }, " sair"))
          )
    )
  );
}
