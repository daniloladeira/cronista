import React, { useEffect } from "react";
import { Box, Text } from "ink";
import { ERRO } from "./theme.js";

const h = React.createElement;

// Erro é temporário, o conteúdo por baixo continua vivo -- some sozinho
// depois de timeoutMs, não precisa de interação pra desaparecer.
export default function Notice({ message, onExpire, timeoutMs = 8000 }) {
  useEffect(() => {
    if (!message) return undefined;
    const id = setTimeout(() => onExpire?.(), timeoutMs);
    return () => clearTimeout(id);
  }, [message, timeoutMs, onExpire]);

  if (!message) return null;
  return h(Box, { marginBottom: 1 }, h(Text, { color: ERRO }, message));
}
