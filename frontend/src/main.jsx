import * as Sentry from "@sentry/react";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

// Observabilidade opcional: só ativa o Sentry se VITE_SENTRY_DSN estiver
// definido no ambiente (ex: arquivo .env local). Sem essa variável, isto é
// um no-op completo — nada é inicializado nem enviado. O Vite substitui
// import.meta.env.VITE_* estaticamente em build, então essa checagem é segura
// mesmo em produção sem custo/telemetria indesejada.
if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    integrations: [],
    tracesSampleRate: 0,
  });
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
