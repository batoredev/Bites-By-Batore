import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "@fontsource-variable/dm-sans";
import "./style.css";
import "./interface.css";
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
if ("serviceWorker" in navigator && !window.location.port.startsWith("517")) {
  window.addEventListener("load", () =>
    navigator.serviceWorker.register("/sw.js").catch(() => undefined),
  );
}
