import React, { useEffect, useState } from "react";
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

  const handleStartCapture = (mode = "simple") => {
    setTranslationMode(mode);
    enablePointerEvents();
    setShowOverlay(true);
  };

  useEffect(() => {
    const onStartCapture = (event) => {
      const mode = event?.detail?.mode === "deep" ? "deep" : "simple";
      handleStartCapture(mode);
    };

    window.addEventListener("reze-overlay:start-capture", onStartCapture);
    return () => {
      window.removeEventListener("reze-overlay:start-capture", onStartCapture);
    };
  }, []);

  const handleFinishCapture = async ({ bbox, screenshot }) => {
    setCaptured({ bbox, screenshot });
    setShowOverlay(false);
    disablePointerEvents();

    try {
      const res = await fetch("http://localhost:8000/process-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // include mode
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
      {/* DRAG-TO-CROP LAYER (only when selecting) */}
      {showOverlay && <CaptureOverlay onCapture={handleFinishCapture} />}

      {/* OVERLAYED TRANSLATION (only after capture + backend) */}
      {captured?.bbox && (
        <div
          id="manga-overlay-output"
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
