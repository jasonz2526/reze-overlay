import React, { useState } from "react";
import CaptureOverlay from "./components/CaptureOverlay/CaptureOverlay";
import MangaOverlay from "./components/MangaOverlay/MangaOverlay";

export default function App() {
  const [showOverlay, setShowOverlay] = useState(false);
  const [captured, setCaptured] = useState(null);

  const [panels, setPanels] = useState(null);
  const [imageSrc, setImageSrc] = useState(null);

  const [translationMode, setTranslationMode] = useState("simple"); // "simple" | "deep"

  // Enable pointer interaction when selecting
  const enablePointerEvents = () => {
    const root = document.getElementById("manga-overlay-root");
    if (root) root.style.pointerEvents = "auto";
  };

  // Disable when idle
  const disablePointerEvents = () => {
    const root = document.getElementById("manga-overlay-root");
    if (root) root.style.pointerEvents = "none";
  };

  const handleStartCapture = () => {
    enablePointerEvents();
    setShowOverlay(true);
  };

  const handleFinishCapture = async ({ bbox, screenshot }) => {
    setCaptured({ bbox, screenshot });
    setShowOverlay(false);
    disablePointerEvents();

    try {
      const res = await fetch("http://localhost:8000/process-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // ✅ include mode
        body: JSON.stringify({ screenshot, mode: translationMode }),
      });

      const data = await res.json();
      console.log("SERVER RESPONSE:", data);

      if (data.success) {
        setPanels(data.result.panels);
        setImageSrc(screenshot);
      }
    } catch (err) {
      console.error("ERROR contacting backend:", err);
    }
  };

  return (
    <>
      {/* BUTTON ALWAYS VISIBLE */}
      <div
        style={{
          position: "fixed",
          top: "16px",
          right: "16px",
          zIndex: 1000000,
          pointerEvents: "auto",
          display: "flex",
          gap: "10px",
          alignItems: "center",
        }}
      >
        {/* Mode selector */}
        <select
          value={translationMode}
          onChange={(e) => setTranslationMode(e.target.value)}
          style={{
            padding: "8px 10px",
            borderRadius: "10px",
            border: "1px solid #4b5563",
            background: "#111827",
            color: "white",
            fontSize: "14px",
          }}
        >
          <option value="simple">Simple</option>
          <option value="deep">Deep</option>
        </select>

        <button
          onClick={handleStartCapture}
          style={{
            padding: "8px 12px",
            background: "#111827",
            color: "white",
            borderRadius: "999px",
            border: "1px solid #4b5563",
            fontSize: "14px",
            cursor: "pointer",
          }}
        >
          Capture Manga Area
        </button>
      </div>

      {/* DRAG-TO-CROP LAYER (only when selecting) */}
      {showOverlay && <CaptureOverlay onCapture={handleFinishCapture} />}

      {/* OVERLAYED TRANSLATION (only after capture + backend) */}
      {captured?.bbox && (
        <div
          id="manga-overlay-root"
          style={{
            position: "absolute",
            left: captured.bbox.x,
            top: captured.bbox.y,
            width: captured.bbox.width,
            height: captured.bbox.height,
            pointerEvents: "none",
            zIndex: 999999,
            overflow: "hidden",
          }}
        >
          {panels && imageSrc && (
            <MangaOverlay imageUrl={imageSrc} panels={panels} debug={false} />
          )}
        </div>
      )}
    </>
  );
}
