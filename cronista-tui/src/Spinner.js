import React, { useEffect, useState } from "react";
import { Text } from "ink";

const h = React.createElement;
const _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
const _INTERVAL_MS = 80;

export default function Spinner({ color }) {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setFrame((f) => (f + 1) % _FRAMES.length), _INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  return h(Text, { color }, _FRAMES[frame]);
}
