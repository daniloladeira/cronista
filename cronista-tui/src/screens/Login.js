import React, { useEffect, useRef, useState } from "react";
import { Box, Text, useInput } from "ink";
import Panel from "../Panel.js";
import TextInput from "../TextInput.js";
import Spinner from "../Spinner.js";
import { login } from "../apiClient.js";
import { DOURADO, ERRO } from "../theme.js";

const h = React.createElement;

// Passos: "usuario" -> "senha" -> "enviando" -> "ok". Erro volta pra
// "senha" com a mensagem na tela (usuário preservado, senha limpa).
export default function Login({ width, focused, onBack, onTyping }) {
  const [step, setStep] = useState("usuario");
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState(null);
  const montado = useRef(true);

  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  // App.js ignora "q" como atalho global enquanto isto estiver true --
  // senão digitar "q" no usuário/senha abriria a confirmação de saída.
  const digitando = focused && (step === "usuario" || step === "senha");
  useEffect(() => {
    onTyping?.(digitando);
    return () => onTyping?.(false);
  }, [digitando, onTyping]);

  function enviar(senhaDigitada) {
    setStep("enviando");
    setErro(null);
    login(usuario, senhaDigitada)
      .then(() => {
        if (!montado.current) return;
        setSenha("");
        setStep("ok");
      })
      .catch((err) => {
        if (!montado.current) return;
        setSenha("");
        setErro(err.message);
        setStep("senha");
      });
  }

  useInput(
    () => {
      setUsuario("");
      setErro(null);
      setStep("usuario");
      onBack();
    },
    { isActive: focused && step === "ok" }
  );

  let corpo;
  if (!focused && step !== "ok") {
    corpo = h(Text, { dimColor: true }, "↵ entra com usuário e senha");
  } else if (step === "ok") {
    corpo = h(
      Box,
      { flexDirection: "column" },
      h(Text, { color: DOURADO }, "Login realizado. Token salvo."),
      h(Text, { dimColor: true }, "Qualquer tecla volta ao menu.")
    );
  } else if (step === "enviando") {
    corpo = h(Box, null, h(Spinner, { color: DOURADO }), h(Text, null, " autenticando..."));
  } else {
    corpo = h(
      Box,
      { flexDirection: "column" },
      erro ? h(Box, { marginBottom: 1 }, h(Text, { color: ERRO }, erro)) : null,
      step === "usuario"
        ? h(TextInput, {
            value: usuario,
            onChange: setUsuario,
            onSubmit: (v) => v.trim() && setStep("senha"),
            onCancel: onBack,
            placeholder: "usuário",
            prefix: "Usuário  ",
            focused,
          })
        : h(Text, null, h(Text, { color: DOURADO }, "Usuário  "), usuario),
      step === "senha"
        ? h(TextInput, {
            value: senha,
            onChange: setSenha,
            onSubmit: (v) => v && enviar(v),
            onCancel: () => {
              setSenha("");
              setErro(null);
              setStep("usuario");
            },
            placeholder: "senha",
            prefix: "Senha    ",
            mask: true,
            focused,
          })
        : null
    );
  }

  return h(Panel, { title: "login", color: DOURADO, width }, corpo);
}
