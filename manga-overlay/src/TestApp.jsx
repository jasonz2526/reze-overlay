import React, { useState } from "react";
import CaptureOverlay from "./components/CaptureOverlay/CaptureOverlay";
import MangaOverlay from "./components/MangaOverlay/MangaOverlay";

export default function TestMangaPage() {
  const [showOverlay, setShowOverlay] = useState(false);
  const [captured, setCaptured] = useState(null);
  const [panels, setPanels] = useState(null);
  const [imageSrc, setImageSrc] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleStart = () => setShowOverlay(true);

  const handleFinishCapture = async ({ bbox, screenshot }) => {
    setCaptured({ bbox, screenshot });
    setShowOverlay(false);
    setIsLoading(true);

    // test mode → bypass backend with mock JSON
    try {
      const res = await fetch("http://localhost:8000/process-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screenshot }),
      });

      const data = await res.json();

      if (data.success) {
        setPanels(data.result.panels);
        setImageSrc(screenshot);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        width: "100vw",
        height: "200vh",
        overflowY: "scroll",
        background: "#222",
        padding: "20px",
        boxSizing: "border-box",
        position: "relative",
      }}
    >
      {/* Capture Button */}
      <button
        onClick={handleStart}
        style={{
          position: "fixed",
          top: "200px",
          right: "20px",
          zIndex: 99999,
          padding: "10px 16px",
          background: "#111",
          color: "white",
          borderRadius: "999px",
          border: "1px solid gray",
          cursor: "pointer",
          pointerEvents: "auto",
        }}
      >
        Capture Area
      </button>

      {/* Fake manga image */}
      <img
        src="/example2.jpg"
        alt="Manga Page"
        style={{
          width: "60%",
          display: "block",
          margin: "0 auto",
        }}
      />

      {/* Drag-to-crop overlay */}
      {showOverlay && <CaptureOverlay onCapture={handleFinishCapture} />}

      {/* ⬇ Overlay with absolute positioning */}
      {captured && (
        <div
        id="manga-overlay-root"
          style={{
             position: "absolute",
             left: captured.bbox.x + "px",
             top: captured.bbox.y + "px",
             width: captured.bbox.width + "px",
             height: captured.bbox.height + "px",
             zIndex: 999999,
          }}
        >
          {panels && imageSrc && (
            <MangaOverlay
              imageUrl={imageSrc}
              panels={panels}
              debug={true}
              loading={isLoading}
            />
          )}
        </div>
      )}
    </div>
  );
}
