import React, { useState, useEffect } from "react";
import html2canvas from "html2canvas";
import "./CaptureOverlay.css";

export default function CaptureOverlay({ onCapture }) {
  const [start, setStart] = useState(null);
  const [end, setEnd] = useState(null);
  const [dragging, setDragging] = useState(false);

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

    // Convert viewport → document coordinates for html2canvas
    const docX = x1 + window.scrollX;
    const docY = y1 + window.scrollY;

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
        el.matches(".__next span")   // fallback
    });

    const croppedCanvas = document.createElement("canvas");
    croppedCanvas.width = width * scale;
    croppedCanvas.height = height * scale;

    const ctx = croppedCanvas.getContext("2d");

    ctx.drawImage(
      canvas,
      docX * scale,
      docY * scale,
      width * scale,
      height * scale,
      0,
      0,
      width * scale,
      height * scale
    );

    const base64 = croppedCanvas.toDataURL("image/png");

    onCapture({
      bbox: { x: x1, y: y1, width, height }, // use viewport coordinates
      screenshot: base64,
    });
  };

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
    <div className="capture-overlay" onMouseDown={handleMouseDown}>
      {(start && end) && (
        <div className="selection-rect" style={rectStyle}></div>
      )}
    </div>
  );
}
