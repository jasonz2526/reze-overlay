import React, { useRef, useState } from "react";
import CaptureOverlay from "./components/CaptureOverlay/CaptureOverlay";
import MangaOverlay from "./components/MangaOverlay/MangaOverlay";

export default function TestMangaPage() {
  const pageRef = useRef(null);

  const [showOverlay, setShowOverlay] = useState(false);
  const [captured, setCaptured] = useState(null); // { bbox: {x,y,width,height}, screenshot }
  const [panels, setPanels] = useState(null);
  const [imageSrc, setImageSrc] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [translationMode, setTranslationMode] = useState("simple"); // "simple" | "deep"

  const handleStart = () => setShowOverlay(true);

  const handleFinishCapture = async ({ bbox, screenshot }) => {
    // bbox from overlay is typically viewport-relative (client coords).
    // Convert to coords relative to the pageRef wrapper.
    const pageEl = pageRef.current;
    if (!pageEl) return;

    const rect = pageEl.getBoundingClientRect();

    // bbox: { x, y, width, height } assumed.
    const relativeBbox = {
      x: bbox.x - rect.left,
      y: bbox.y - rect.top,
      width: bbox.width,
      height: bbox.height,
    };

    setCaptured({ bbox: relativeBbox, screenshot });
    setShowOverlay(false);
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/process-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screenshot, mode: translationMode }),
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
        minHeight: "200vh",
        background: "#222",
        padding: "24px",
        boxSizing: "border-box",
      }}
    >
      {/* Top-right controls */}
      <div
        style={{
          position: "fixed",
          top: "16px",
          right: "16px",
          zIndex: 1000000,
          display: "flex",
          gap: "10px",
          alignItems: "center",
          pointerEvents: "auto",
        }}
      >
        {/* Simple toggle (optional) */}
        <select
          value={translationMode}
          onChange={(e) => setTranslationMode(e.target.value)}
          style={{
            padding: "8px 10px",
            borderRadius: "10px",
            border: "1px solid #4b5563",
            background: "#111",
            color: "white",
          }}
        >
          <option value="simple">Simple</option>
          <option value="deep">Deep</option>
        </select>

        <button
          onClick={handleStart}
          style={{
            padding: "10px 16px",
            background: "#111",
            color: "white",
            borderRadius: "999px",
            border: "1px solid gray",
            cursor: "pointer",
          }}
        >
          Capture Area
        </button>
      </div>

      {/* Centered page wrapper = ONE coordinate space */}
      <div
        ref={pageRef}
        style={{
          width: "60%",
          margin: "0 auto",
          position: "relative", // IMPORTANT: overlay anchors here
        }}
      >
        {/* Your fake manga image */}
        <img
          src="/example2.jpg"
          alt="Manga Page"
          style={{
            width: "100%",
            display: "block",
          }}
        />

        {/* Overlay sits on top of the image wrapper */}
        {captured?.bbox && (
          <div
            id="manga-overlay-root"
            style={{
              position: "absolute",
              left: `${captured.bbox.x}px`,
              top: `${captured.bbox.y}px`,
              width: `${captured.bbox.width}px`,
              height: `${captured.bbox.height}px`,
              zIndex: 999999,
              pointerEvents: "none",
              overflow: "hidden",
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

      {/* Drag-to-crop overlay */}
      {showOverlay && <CaptureOverlay onCapture={handleFinishCapture} />}
    </div>
  );
}
