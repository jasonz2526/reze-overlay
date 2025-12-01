import React, { useRef, useEffect, useState } from "react";
import "./mangaOverlay.css";

export default function MangaOverlay({ imageUrl, panels, debug = false }) {
  const containerRef = useRef(null);
  const imgRef = useRef(null);
  const canvasRef = useRef(null);

  const [scale, setScale] = useState(1);
  const [baseFontSize, setBaseFontSize] = useState(24);  // NEW GLOBAL FONT SIZE

  /*SCALE COMPUTATION*/
  useEffect(() => {
    const updateScale = () => {
      if (!containerRef.current || !imgRef.current) return;

      const containerWidth = containerRef.current.clientWidth;
      const naturalWidth = imgRef.current.naturalWidth;
      if (!naturalWidth) return;

      setScale(containerWidth / naturalWidth);
    };

    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, []);

  /*DRAW MASKS*/
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx || !imgRef.current) return;

    canvas.width = imgRef.current.naturalWidth * scale;
    canvas.height = imgRef.current.naturalHeight * scale;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    panels.forEach(panel => {
      panel.bubbles.forEach(b => drawBubbleMask(ctx, b.bbox, scale));
      panel.outside_text.forEach(t => drawOutsideMask(ctx, t.bbox, scale));
    });
  }, [scale, panels]);

  /*BUBBLE & TEXT MASKS*/
  const drawBubbleMask = (ctx, bbox, scale) => {
    const [x1, y1, x2, y2] = bbox;
    const x = x1 * scale;
    const y = y1 * scale;
    const w = (x2 - x1) * scale;
    const h = (y2 - y1) * scale;

    const cx = x + w / 2;
    const cy = y + h / 2;

    let rx = (w / 2) * 0.94;
    let ry = (h / 2) * 0.94;

    ctx.save();
    ctx.fillStyle = "white";
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  };

  const drawOutsideMask = (ctx, bbox, scale) => {
    const [x1, y1, x2, y2] = bbox;
    ctx.save();
    ctx.fillStyle = "rgba(255,255,255,0.95)";
    ctx.fillRect(x1 * scale, y1 * scale, (x2 - x1) * scale, (y2 - y1) * scale);
    ctx.restore();
  };

  /*GLOBAL FONT SIZE CALC */
  useEffect(() => {
    // Measure all text lengths to decide page-wide font size
    let longest = 0;

    panels.forEach(panel => {
      panel.bubbles.forEach(b => {
        longest = Math.max(longest, (b.en || "").length);
      });
      panel.outside_text.forEach(t => {
        longest = Math.max(longest, (t.en || "").length);
      });
    });

    // Map longest bubble text to a font size (consistent across page)
    let base = 16;     // default
    if (longest > 50) base = 12;
    if (longest > 80) base = 10;
    if (longest > 120) base = 8;

    setBaseFontSize(base);
  }, [panels]);

  /*BUBBLE STYLE*/
  const boxStyle = (bbox) => {
    const [x1, y1, x2, y2] = bbox;
    const w = (x2 - x1) * scale;
    const h = (y2 - y1) * scale;

    // Padding inside bubble to keep text well centered
    const padX = Math.min(22, w * 0.10);
    const padY = Math.min(14, h * 0.08);

    return {
      position: "absolute",
      left: `${x1 * scale}px`,
      top: `${y1 * scale}px`,
      width: `${w}px`,
      height: `${h}px`,
      padding: `${padY}px ${padX}px`,
      boxSizing: "border-box",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    };
  };

  /*AUTO SHRINK ONLY IF NECESSARY*/
  const useBubbleFont = () => {
    const ref = useRef(null);

    useEffect(() => {
      const el = ref.current;
      if (!el) return;

      const parent = el.parentElement;
      if (!parent) return;

      // Start with the global base font size
      let size = baseFontSize * scale;
      el.style.fontSize = `${size}px`;

      let attempts = 0;

      while (attempts < 10 && el.scrollHeight > parent.clientHeight) {
        size *= 0.9; // shrink only if overflowing
        el.style.fontSize = `${size}px`;
        attempts++;
      }
    }, [baseFontSize, scale]);

    return ref;
  };

  return (
    <div ref={containerRef} className="manga-container">
      <img ref={imgRef} src={imageUrl} className="manga-img" />

      <canvas ref={canvasRef} className="mask-canvas" />

      <div className="text-layer">
        {panels.map((panel, pIdx) => (
          <React.Fragment key={pIdx}>
            {panel.bubbles.map((b, bIdx) => {
              const textRef = useBubbleFont();
              return (
                <div key={`bubble-${bIdx}`} className="bubble-text" style={boxStyle(b.bbox)}>
                  <div className="text-inner" ref={textRef}>{b.en}</div>
                </div>
              );
            })}

            {panel.outside_text.map((t, tIdx) => {
              const textRef = useBubbleFont();
              return (
                <div key={`text-${tIdx}`} className="outside-text" style={boxStyle(t.bbox)}>
                  <div className="text-inner" ref={textRef}>{t.en}</div>
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>

      {debug && (
        <div className="debug-layer">
          {panels.map((panel, pIdx) => (
            <React.Fragment key={pIdx}>
              {panel.bubbles.map((b, i) => (
                <div key={`db-b${i}`} className="debug-box" style={boxStyle(b.bbox)} />
              ))}
              {panel.outside_text.map((t, j) => (
                <div key={`db-t${j}`} className="debug-box outside" style={boxStyle(t.bbox)} />
              ))}
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}
