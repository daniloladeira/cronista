export function lerpColor(baseHex, targetHex, t) {
  t = Math.max(0, Math.min(1, t));
  const r1 = parseInt(baseHex.slice(1, 3), 16);
  const g1 = parseInt(baseHex.slice(3, 5), 16);
  const b1 = parseInt(baseHex.slice(5, 7), 16);
  const r2 = parseInt(targetHex.slice(1, 3), 16);
  const g2 = parseInt(targetHex.slice(3, 5), 16);
  const b2 = parseInt(targetHex.slice(5, 7), 16);
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  const hex = (n) => n.toString(16).padStart(2, "0");
  return `#${hex(r)}${hex(g)}${hex(b)}`;
}

export function shimmerPosition(startedAtMs, wordLen, flashWidth, sweepSeconds, pauseSeconds) {
  const cycle = sweepSeconds + pauseSeconds;
  const elapsed = (((Date.now() - startedAtMs) / 1000) % cycle);
  if (elapsed > sweepSeconds) return -999;
  const span = wordLen + 2 * flashWidth;
  return -flashWidth + span * (elapsed / sweepSeconds);
}

export function shimmerChars(word, position, baseHex, flashHex, flashWidth) {
  return Array.from(word).map((ch, i) => {
    const distance = Math.abs(i - position);
    const intensity = Math.max(0, 1 - distance / flashWidth);
    return { ch, color: lerpColor(baseHex, flashHex, intensity) };
  });
}
