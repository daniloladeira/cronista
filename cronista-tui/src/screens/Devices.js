import React, { useEffect, useState } from "react";
import { execFile } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { Box, Text, useInput } from "ink";
import Panel from "../Panel.js";
import DeviceTable from "../DeviceTable.js";
import { DOURADO, ERRO } from "../theme.js";

const h = React.createElement;
const __dirname = path.dirname(fileURLToPath(import.meta.url));

function loadDevices() {
  return new Promise((resolve, reject) => {
    const pythonExe = path.join(__dirname, "..", "..", "..", ".venv", "Scripts", "python.exe");
    const script = path.join(__dirname, "..", "..", "devices.py");
    execFile(pythonExe, [script], { encoding: "utf-8" }, (err, stdout) => {
      if (err) reject(err);
      else resolve(JSON.parse(stdout));
    });
  });
}

export default function Devices({ width, focused, onBack }) {
  const [state, setState] = useState({ status: "carregando" });

  useInput(
    (input, key) => {
      if (key.escape || key.leftArrow) onBack();
    },
    { isActive: focused }
  );

  useEffect(() => {
    let cancelado = false;
    loadDevices()
      .then((devices) => !cancelado && setState({ status: "ok", devices }))
      .catch((err) => !cancelado && setState({ status: "erro", message: String(err) }));
    return () => {
      cancelado = true;
    };
  }, []);

  if (state.status === "carregando") return h(Text, { dimColor: true }, "Consultando dispositivos…");
  if (state.status === "erro") return h(Text, { color: ERRO }, state.message);

  return h(
    Box,
    { flexDirection: "column" },
    h(Box, { marginBottom: 1 }, h(Panel, { title: "entrada (microfone)", color: DOURADO, width }, h(DeviceTable, { devices: state.devices.entrada }))),
    h(Panel, { title: "saída (loopback)", color: DOURADO, width }, h(DeviceTable, { devices: state.devices.saida }))
  );
}
