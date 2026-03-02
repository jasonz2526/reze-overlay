import React, { useEffect, useRef, useState } from "react";
import CaptureOverlay from "./components/CaptureOverlay/CaptureOverlay";
import MangaOverlay from "./components/MangaOverlay/MangaOverlay";

export default function App() {
  const [showOverlay, setShowOverlay] = useState(false);
  const [captured, setCaptured] = useState(null);

  const [panels, setPanels] = useState(null);
  const [imageSrc, setImageSrc] = useState(null);
  const [processingCount, setProcessingCount] = useState(0);

  const [translationMode, setTranslationMode] = useState("simple"); // "simple" | "deep"
  const [autoRecaptureOnArrow, setAutoRecaptureOnArrow] = useState(false);
  const isProcessing = processingCount > 0;

  const capturedRef = useRef(null);
  const modeRef = useRef("simple");
  const autoRecaptureRef = useRef(false);
  const showOverlayRef = useRef(false);
  const recaptureInFlightRef = useRef(false);
  const recaptureTimerRef = useRef(null);
  const suppressAutoRecaptureUntilRef = useRef(0);

  useEffect(() => {
    capturedRef.current = captured;
  }, [captured]);

  useEffect(() => {
    modeRef.current = translationMode;
  }, [translationMode]);

  useEffect(() => {
    autoRecaptureRef.current = autoRecaptureOnArrow;
  }, [autoRecaptureOnArrow]);

  useEffect(() => {
    showOverlayRef.current = showOverlay;
  }, [showOverlay]);

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

  const handleStartCapture = (mode = "simple", autoRecapture = false) => {
    // Keep refs in sync immediately to avoid async state timing issues.
    modeRef.current = mode;
    autoRecaptureRef.current = autoRecapture;
    setTranslationMode(mode);
    setAutoRecaptureOnArrow(autoRecapture);
    enablePointerEvents();
    setShowOverlay(true);
  };

  useEffect(() => {
    const onStartCapture = (event) => {
      const mode = event?.detail?.mode === "deep" ? "deep" : "simple";
      const autoRecapture = Boolean(event?.detail?.autoRecaptureOnArrow);
      handleStartCapture(mode, autoRecapture);
    };

    const onUpdateSettings = (event) => {
      const autoRecapture = Boolean(event?.detail?.autoRecaptureOnArrow);
      setAutoRecaptureOnArrow(autoRecapture);
    };

    window.addEventListener("reze-overlay:start-capture", onStartCapture);
    window.addEventListener("reze-overlay:update-settings", onUpdateSettings);
    return () => {
      window.removeEventListener("reze-overlay:start-capture", onStartCapture);
      window.removeEventListener("reze-overlay:update-settings", onUpdateSettings);
    };
  }, []);

  const translateScreenshot = async (screenshot, mode) => {
    const effectiveMode = mode === "deep" ? "deep" : "simple";
    const startedAt = Date.now();
    setProcessingCount((count) => count + 1);
    console.log("Translating screenshot with mode:", effectiveMode);

    try {
      const res = await fetch("http://localhost:8000/process-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screenshot, mode: effectiveMode }),
      });

      const data = await res.json();
      console.log("SERVER RESPONSE:", data);

      if (data.success) {
        setPanels(data.result.panels);
        setImageSrc(screenshot);
      } else {
        console.error("Translation failed:", data.error || "unknown server error");
      }
    } catch (err) {
      console.error("ERROR contacting backend:", err);
    } finally {
      const elapsed = Date.now() - startedAt;
      if (elapsed < 300) {
        await new Promise((resolve) => setTimeout(resolve, 300 - elapsed));
      }
      setProcessingCount((count) => Math.max(0, count - 1));
    }
  };

  const handleFinishCapture = async ({ bbox, screenshot }) => {
    const docBbox = {
      x: bbox.x + window.scrollX,
      y: bbox.y + window.scrollY,
      width: bbox.width,
      height: bbox.height,
    };

    setCaptured({
      bboxViewport: bbox,
      bboxDoc: docBbox,
      screenshot,
    });
    setShowOverlay(false);
    disablePointerEvents();
    await translateScreenshot(screenshot, modeRef.current);
  };

  const waitForCaptureScreen = (requestId) =>
    new Promise((resolve) => {
      const timeout = setTimeout(() => {
        window.removeEventListener("reze-overlay:capture-screen-response", onResponse);
        resolve(null);
      }, 2500);

      const onResponse = (event) => {
        const detail = event?.detail;
        if (!detail || detail.requestId !== requestId) return;
        clearTimeout(timeout);
        window.removeEventListener("reze-overlay:capture-screen-response", onResponse);
        resolve(detail.screenshot || null);
      };

      window.addEventListener("reze-overlay:capture-screen-response", onResponse);
      window.dispatchEvent(
        new CustomEvent("reze-overlay:capture-screen-request", {
          detail: { requestId },
        })
      );
    });

  const cropDataUrlToBbox = (dataUrl, bbox) =>
    new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const viewportW = window.innerWidth || 1;
        const viewportH = window.innerHeight || 1;
        const scaleX = img.naturalWidth / viewportW;
        const scaleY = img.naturalHeight / viewportH;

        const sx = Math.max(0, Math.floor(bbox.x * scaleX));
        const sy = Math.max(0, Math.floor(bbox.y * scaleY));
        const sw = Math.max(1, Math.floor(bbox.width * scaleX));
        const sh = Math.max(1, Math.floor(bbox.height * scaleY));

        const canvas = document.createElement("canvas");
        canvas.width = sw;
        canvas.height = sh;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          resolve(null);
          return;
        }

        ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
        resolve(canvas.toDataURL("image/png"));
      };
      img.onerror = () => resolve(null);
      img.src = dataUrl;
    });

  const recaptureFromCurrentBox = async () => {
    if (recaptureInFlightRef.current) return;
    const current = capturedRef.current;
    if (!current?.bboxDoc) return;

    recaptureInFlightRef.current = true;
    suppressAutoRecaptureUntilRef.current = Date.now() + 1600;
    try {
      const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const fullScreenshot = await waitForCaptureScreen(requestId);
      if (!fullScreenshot) return;

      const viewportBbox = {
        x: current.bboxDoc.x - window.scrollX,
        y: current.bboxDoc.y - window.scrollY,
        width: current.bboxDoc.width,
        height: current.bboxDoc.height,
      };

      const croppedScreenshot = await cropDataUrlToBbox(fullScreenshot, viewportBbox);
      if (!croppedScreenshot) return;

      setCaptured({
        bboxViewport: viewportBbox,
        bboxDoc: current.bboxDoc,
        screenshot: croppedScreenshot,
      });
      await translateScreenshot(croppedScreenshot, modeRef.current);
    } catch (err) {
      console.warn("Auto recapture failed:", err);
    } finally {
      recaptureInFlightRef.current = false;
    }
  };

  useEffect(() => {
    const clearRenderedOverlay = () => {
      setPanels(null);
      setImageSrc(null);
    };

    const scheduleAutoRecapture = (delayMs = 350) => {
      if (recaptureTimerRef.current) {
        clearTimeout(recaptureTimerRef.current);
      }
      clearRenderedOverlay();
      recaptureTimerRef.current = setTimeout(() => {
        recaptureFromCurrentBox();
      }, delayMs);
    };

    const isLikelyReaderNavClick = (target) => {
      if (!target) return false;
      const el = target.closest?.("button, a, [role='button'], [aria-label], [title]");
      if (!el) return false;

      const text = (el.textContent || "").toLowerCase();
      const aria = (el.getAttribute?.("aria-label") || "").toLowerCase();
      const title = (el.getAttribute?.("title") || "").toLowerCase();
      const className = (typeof el.className === "string" ? el.className : "").toLowerCase();
      const id = (el.id || "").toLowerCase();
      const signature = `${text} ${aria} ${title} ${className} ${id}`;

      return [
        "next",
        "prev",
        "previous",
        "arrow",
        "right",
        "left",
        "forward",
        "back",
      ].some((token) => signature.includes(token));
    };

    const onArrowNavigate = (event) => {
      if (!autoRecaptureRef.current) return;
      if (showOverlayRef.current) return;
      if (!capturedRef.current?.bboxDoc) return;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;

      const target = event.target;
      const isEditable =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if (isEditable) return;

      // Remove stale overlay immediately, then recapture after reader renders.
      scheduleAutoRecapture(350);
    };

    const onLikelyNavClick = (event) => {
      if (!autoRecaptureRef.current) return;
      if (showOverlayRef.current) return;
      if (!capturedRef.current?.bboxDoc) return;
      if (event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if (!isLikelyReaderNavClick(event.target)) return;

      // Click-based readers usually need slightly longer to repaint.
      scheduleAutoRecapture(420);
    };

    window.addEventListener("keydown", onArrowNavigate);
    window.addEventListener("click", onLikelyNavClick, true);
    return () => {
      window.removeEventListener("keydown", onArrowNavigate);
      window.removeEventListener("click", onLikelyNavClick, true);
      if (recaptureTimerRef.current) {
        clearTimeout(recaptureTimerRef.current);
      }
    };
  }, []);

  return (
    <>
      {/* DRAG-TO-CROP LAYER (only when selecting) */}
      {showOverlay && <CaptureOverlay onCapture={handleFinishCapture} />}

      {/* OVERLAYED TRANSLATION (only after capture + backend) */}
      {captured?.bboxDoc && (
        <div
          id="manga-overlay-output"
          style={{
            position: "absolute",
            left: captured.bboxDoc.x,
            top: captured.bboxDoc.y,
            width: captured.bboxDoc.width,
            height: captured.bboxDoc.height,
            pointerEvents: "none",
            zIndex: 999999,
            overflow: "hidden",
          }}
        >
          {isProcessing && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                zIndex: 1000002,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "rgba(17, 24, 39, 0.38)",
                backdropFilter: "blur(1px)",
                pointerEvents: "none",
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 8,
                  background: "rgba(17, 24, 39, 0.86)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: 12,
                  padding: "10px 14px",
                }}
              >
                <svg
                  width="26"
                  height="26"
                  viewBox="0 0 50 50"
                  aria-label="Loading"
                  role="img"
                >
                  <circle
                    cx="25"
                    cy="25"
                    r="20"
                    fill="none"
                    stroke="rgba(255,255,255,0.25)"
                    strokeWidth="4"
                  />
                  <path
                    d="M25 5a20 20 0 0 1 20 20"
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth="4"
                    strokeLinecap="round"
                  >
                    <animateTransform
                      attributeName="transform"
                      type="rotate"
                      from="0 25 25"
                      to="360 25 25"
                      dur="0.8s"
                      repeatCount="indefinite"
                    />
                  </path>
                </svg>
                <div
                  style={{
                    color: "#fff",
                    fontSize: 12,
                    fontWeight: 700,
                    letterSpacing: "0.01em",
                  }}
                >
                  Translating...
                </div>
              </div>
            </div>
          )}

          {panels && imageSrc && (
            <MangaOverlay imageUrl={imageSrc} panels={panels} debug={false} />
          )}
        </div>
      )}
    </>
  );
}
