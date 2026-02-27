// manga-overlay/src/main.jsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import TestApp from "./TestApp";

const RootApp = import.meta.env.VITE_APP_MODE === "test" ? TestApp : App;

// Try to find the overlay root (injected by extension)
const existing = document.getElementById("manga-overlay-root");

let container = existing;
if (!container) {
  // Fallback for running standalone via Vite dev server
  container = document.getElementById("root");
}

if (!container) {
  // Last resort: create a root if nothing exists
  const div = document.createElement("div");
  div.id = "manga-overlay-root";
  document.body.appendChild(div);
  container = div;
}

const root = ReactDOM.createRoot(container);
root.render(
  <React.StrictMode>
    <RootApp />
  </React.StrictMode>
);
