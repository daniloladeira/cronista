import React, { useEffect, useState } from "react";
import { Box, Text, useInput } from "ink";
import Panel from "../Panel.js";
import MeetingList from "../MeetingList.js";
import MeetingDetail from "../MeetingDetail.js";
import TextInput from "../TextInput.js";
import Notice from "../Notice.js";
import { listMeetings, getMeeting, getTranscript, search } from "../apiClient.js";
import { DOURADO } from "../theme.js";

const h = React.createElement;

// Agrupa por reunião, primeira ocorrência (já vem ordenado por relevância).
function meetingsFromSearchResults(results) {
  const seen = new Map();
  for (const r of results) {
    if (!seen.has(r.meeting_id)) {
      seen.set(r.meeting_id, { id: r.meeting_id, title: r.meeting_title, status: `trecho: "${r.text.slice(0, 40)}"` });
    }
  }
  return [...seen.values()];
}

// Um modo por vez ("list", "detail", "search"), cada useInput ativo só
// no seu modo pra não competir pela mesma tecla.
export default function Meetings({ width, height, focused, onBack, initialMeetingId = null, initialSearchTerm = null }) {
  const [loading, setLoading] = useState(true);
  const [meetings, setMeetings] = useState([]);
  const [notice, setNotice] = useState(null);
  const [cursor, setCursor] = useState(0);
  const [mode, setMode] = useState("list"); // "list" | "detail" | "search"
  const [searchValue, setSearchValue] = useState("");
  const [detail, setDetail] = useState(null); // { meeting, segments } | null
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let cancelado = false;
    // Busca OU lista primeiro, nunca as duas; abre a reunião inicial
    // depois, se veio uma.
    const carga = initialSearchTerm ? search(initialSearchTerm) : listMeetings();
    carga
      .then((data) => {
        if (cancelado) return;
        const lista = initialSearchTerm ? meetingsFromSearchResults(data) : data;
        setMeetings(lista);
        setLoading(false);
        if (initialMeetingId) abrirReuniao(initialMeetingId);
      })
      .catch((err) => {
        if (cancelado) return;
        setNotice(err.message);
        setLoading(false);
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function abrirReuniao(meetingId) {
    setDetailLoading(true);
    Promise.all([getMeeting(meetingId), getTranscript(meetingId)])
      .then(([meeting, segments]) => {
        setDetail({ meeting, segments });
        setMode("detail");
        setDetailLoading(false);
      })
      .catch((err) => {
        setNotice(err.message);
        setDetailLoading(false);
      });
  }

  function submeterBusca(termo) {
    const q = termo.trim();
    setMode("list");
    if (!q) return;
    setLoading(true);
    search(q)
      .then((results) => {
        setMeetings(meetingsFromSearchResults(results));
        setCursor(0);
        setLoading(false);
      })
      .catch((err) => {
        setNotice(err.message);
        setLoading(false);
      });
  }

  useInput(
    (input, key) => {
      if (meetings.length > 0) {
        if (key.upArrow || input === "k") setCursor((c) => (c - 1 + meetings.length) % meetings.length);
        else if (key.downArrow || input === "j") setCursor((c) => (c + 1) % meetings.length);
        else if (key.return) abrirReuniao(meetings[cursor].id);
      }
      if (input === "/") {
        setSearchValue("");
        setMode("search");
        return;
      }
      if (key.escape || key.leftArrow) onBack();
    },
    { isActive: focused && mode === "list" && !loading && !detailLoading }
  );

  if (mode === "detail" && detail) {
    return h(MeetingDetail, {
      meeting: detail.meeting,
      segments: detail.segments,
      width,
      height,
      focused: focused && mode === "detail",
      onBack: () => setMode("list"),
    });
  }

  const body = h(
    Box,
    { flexDirection: "column" },
    h(Notice, { message: notice, onExpire: () => setNotice(null) }),
    mode === "search"
      ? h(TextInput, {
          value: searchValue,
          onChange: setSearchValue,
          onSubmit: submeterBusca,
          onCancel: () => setMode("list"),
          placeholder: "Buscar…",
          focused: focused && mode === "search",
        })
      : null,
    loading || detailLoading
      ? h(Text, { dimColor: true }, detailLoading ? "Abrindo reunião…" : "Consultando reuniões…")
      : h(MeetingList, { meetings, cursor, focused: focused && mode === "list" })
  );

  return h(Panel, { title: "reuniões", color: DOURADO, width, height }, body);
}
