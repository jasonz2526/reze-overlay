import React, { useState, useEffect } from "react";
import html2canvas from "html2canvas";
import "./CaptureOverlay.css";

export default function CaptureOverlay({ onCapture }) {
  const [start, setStart] = useState(null);
  const [end, setEnd] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [isSnapshotting, setIsSnapshotting] = useState(false);

  const handleMouseDown = (e) => {
    setDragging(true);
    setStart({ x: e.clientX, y: e.clientY });
    setEnd({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e) => {
    if (!dragging) return;
    setEnd({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = async () => {
    setDragging(false);
    if (!start || !end) return;

    const x1 = Math.min(start.x, end.x);
    const y1 = Math.min(start.y, end.y);
    const width = Math.abs(end.x - start.x);
    const height = Math.abs(end.y - start.y);
    if (width < 2 || height < 2) return;

    // Hide overlay/selection before screenshot so capture does not include blue highlight.
    setIsSnapshotting(true);
    setStart(null);
    setEnd(null);
    await waitForNextPaint();

    const base64 =
      (await captureViaExtensionScreenshot({ x: x1, y: y1, width, height })) ||
      (await captureViaHtml2Canvas({ x: x1, y: y1, width, height }));

    if (!base64) return;

    onCapture({
      bbox: { x: x1, y: y1, width, height }, // use viewport coordinates
      screenshot: base64,
    });
  };

  const waitForNextPaint = () =>
    new Promise((resolve) => {
      requestAnimationFrame(() => {
        requestAnimationFrame(resolve);
      });
    });

  const captureViaExtensionScreenshot = async (bbox) => {
    try {
      const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;

      const screenshot = await new Promise((resolve) => {
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

      if (!screenshot) return null;
      return await cropDataUrlToBbox(screenshot, bbox);
    } catch (err) {
      console.warn("Extension screenshot capture failed, falling back:", err);
      return null;
    }
  };

  const captureViaHtml2Canvas = async (bbox) => {
    try {
      // Convert viewport -> document coordinates for html2canvas
      const docX = bbox.x + window.scrollX;
      const docY = bbox.y + window.scrollY;
      const scale = window.devicePixelRatio;

      const canvas = await html2canvas(document.body, {
        useCORS: true,
        scale,
        logging: false,
        ignoreElements: (el) =>
          el.classList?.contains("capture-overlay") ||
          el.classList?.contains("selection-rect") ||
          el.matches("._viewport_1kgtc_15 span") ||
          el.matches("._cover_1gu97_16") ||
          el.matches("._root_75tnq_7 span") ||
          el.matches(".__next span"),
      });

      const croppedCanvas = document.createElement("canvas");
      croppedCanvas.width = bbox.width * scale;
      croppedCanvas.height = bbox.height * scale;

      const ctx = croppedCanvas.getContext("2d");
      if (!ctx) return null;

      ctx.drawImage(
        canvas,
        docX * scale,
        docY * scale,
        bbox.width * scale,
        bbox.height * scale,
        0,
        0,
        bbox.width * scale,
        bbox.height * scale
      );

      return croppedCanvas.toDataURL("image/png");
    } catch (err) {
      console.error("html2canvas capture failed:", err);
      return null;
    }
  };

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

  useEffect(() => {
    const move = (e) => handleMouseMove(e);
    const up = () => handleMouseUp();

    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);

    return () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    };
  });

  let rectStyle = {};
  if (start && end) {
    const x = Math.min(start.x, end.x);
    const y = Math.min(start.y, end.y);
    const w = Math.abs(end.x - start.x);
    const h = Math.abs(end.y - start.y);

    rectStyle = {
      left: x,
      top: y,
      width: w,
      height: h,
      display: "block",
    };
  }

  return (
    <div
      className={`capture-overlay${isSnapshotting ? " capture-overlay-hidden" : ""}`}
      onMouseDown={isSnapshotting ? undefined : handleMouseDown}
    >
      {start && end && !isSnapshotting && (
        <div className="selection-rect" style={rectStyle}></div>
      )}
    </div>
  );
}
