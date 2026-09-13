import React from "react";
import { Text } from "ink";

const h = React.createElement;

export default function Rule({ width, color }) {
  return h(Text, { color }, "─".repeat(Math.max(1, width)));
}
