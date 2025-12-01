import React, { useRef, useEffect, useState } from "react";
import "./mangaOverlay.css";

export default function MangaOverlay({ imageUrl, panels, debug = false }) {
  if (!imageUrl || !panels || panels.length === 0) {
    console.warn("MangaOverlay: Missing image or panels");
    return null;
  }

  const containerRef = useRef(null);
  const imgRef = useRef(null);
  const canvasRef = useRef(null);

  const [scale, setScale] = useState(1);
  const [baseFontSize, setBaseFontSize] = useState(20);

  // NEW: cache outside text font sizes
  const [outsideFontSizes, setOutsideFontSizes] = useState({});

  /* ------------------------------------------
   * Compute scale based on the rendered image
   * ---------------------------------------- */
  useEffect(() => {
    const updateScale = () => {
      if (!containerRef.current || !imgRef.current) return;

      const containerWidth = containerRef.current.clientWidth;
      const naturalWidth = imgRef.current.naturalWidth;

      if (naturalWidth > 0) {
        setScale(containerWidth / naturalWidth);
      }
    };

    updateScale();
    window.addEventListener("resize", updateScale);

    return () => window.removeEventListener("resize", updateScale);
  }, [imageUrl]);

  /* ------------------------------------------
   * Draw bubble + outside masks on canvas
   * ---------------------------------------- */
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const img = imgRef.current;

    if (!canvas || !ctx || !img) return;
    if (!img.naturalWidth || !img.naturalHeight) return;

    canvas.width = img.naturalWidth * scale;
    canvas.height = img.naturalHeight * scale;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    panels.forEach((panel) => {
      panel.bubbles?.forEach((bubble) => {
        if (bubble?.bbox) drawBubbleMask(ctx, bubble.bbox, scale);
      });

      panel.outside_text?.forEach((t) => {
        if (t?.bbox) drawOutsideMask(ctx, t.bbox, scale);
      });
    });
  }, [scale, panels]);

  /* ------------------------------------------
   * Mask drawing helpers
   * ---------------------------------------- */
  const drawBubbleMask = (ctx, bbox, scale) => {
    const [x1, y1, x2, y2] = bbox;

    const x = x1 * scale;
    const y = y1 * scale;
    const w = (x2 - x1) * scale;
    const h = (y2 - y1) * scale;

    const cx = x + w / 2;
    const cy = y + h / 2;

    const rx = (w / 2) * 0.94;
    const ry = (h / 2) * 0.94;

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
    ctx.fillRect(
      x1 * scale,
      y1 * scale,
      (x2 - x1) * scale,
      (y2 - y1) * scale
    );
    ctx.restore();
  };

  /* ------------------------------------------
   * Compute bubble-wide font size
   * ---------------------------------------- */
  useEffect(() => {
    let longest = 0;

    panels.forEach((panel) => {
      panel.bubbles?.forEach((b) => {
        longest = Math.max(longest, (b.en || "").length);
      });
    });

    let size = 24;
    if (longest > 60) size = 22;
    if (longest > 90) size = 18;
    if (longest > 120) size = 14
    
    setBaseFontSize(size);
  }, [panels]);

  /* ------------------------------------------
   * Helper: compute max fitting font size
   * ---------------------------------------- */
  const computeMaxFontSize = (text, maxW, maxH) => {
    // NEW: Define minimum thresholds
    const MIN_BOX_SIZE = 5; 
    const min = 6;
    
    // NEW: Check for impossibly small boxes and return min font size immediately
    if (maxW < MIN_BOX_SIZE || maxH < MIN_BOX_SIZE) {
      return min;
    }
    
    const tester = document.createElement("div");
  
    tester.style.position = "absolute";
    tester.style.visibility = "hidden";
    // CHANGED: Use normal white-space to allow forced word breaking 
    tester.style.whiteSpace = "normal"; 
    tester.style.lineHeight = "1.15"; 
    tester.style.fontFamily = "'Comic Neue', Arial, sans-serif";
    tester.style.textAlign = "center";
    tester.style.padding = "0";
    tester.style.width = `${maxW}px`;
    tester.style.boxSizing = "content-box"; 
    // Add overflow-wrap for tester to match CSS behavior
    tester.style.overflowWrap = "break-word"; 
  
    tester.innerText = text;
    document.body.appendChild(tester);
  
    let font = 22;                    // start reasonably small
  
    while (font > min) {
      tester.style.fontSize = `${font}px`;
  
      if (tester.scrollHeight <= maxH) break;
  
      font -= 1;
    }
  
    document.body.removeChild(tester);
    return font;
  };
  

  /* ------------------------------------------
   * Compute OUTSIDE text font sizes AFTER
   * bubble font/layout is stable
   * ---------------------------------------- */
  useEffect(() => {
    if (!scale) return;
  
    const newSizes = {};
    const paddingFactor = 0.85; // shrink usable area slightly
  
    panels.forEach((panel, pIdx) => {
      panel.outside_text?.forEach((t, tIdx) => {
        const [x1, y1, x2, y2] = t.bbox;
  
        const boxW = (x2 - x1) * scale;
        const boxH = (y2 - y1) * scale;
  
        // leave some padding inside box
        const usableW = boxW * paddingFactor;
        const usableH = boxH * paddingFactor;
  
        newSizes[`${pIdx}-${tIdx}`] = computeMaxFontSize(
          t.en,
          usableW,
          usableH
        );
      });
    });
  
    setOutsideFontSizes(newSizes);
  }, [panels, scale]);
  

  /* ------------------------------------------
   * Bubble text (shared font)
   * ---------------------------------------- */
  const useBubbleFont = () => {
    const ref = useRef(null);

    useEffect(() => {
      const el = ref.current;
      const parent = el?.parentElement;
      if (!el || !parent) return;

      let size = baseFontSize * scale;
      el.style.fontSize = `${size}px`;

      let attempts = 0;
      while (attempts < 12 && el.scrollHeight > parent.clientHeight) {
        size -= 2;
        el.style.fontSize = `${size}px`;
        attempts++;
      }
    }, [baseFontSize, scale]);

    return ref;
  };

  /* ------------------------------------------
   * Box style helper
   * ---------------------------------------- */
  const boxStyle = (bbox) => {
    const [x1, y1, x2, y2] = bbox;

    return {
      position: "absolute",
      left: `${x1 * scale}px`,
      top: `${y1 * scale}px`,
      width: `${(x2 - x1) * scale}px`,
      height: `${(y2 - y1) * scale}px`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      overflow: "hidden",
      textAlign: "center",
      boxSizing: "border-box", 
    };
  };

  /* ------------------------------------------
   * RENDER
   * ---------------------------------------- */
  return (
    <div ref={containerRef} className="manga-container">
      <img ref={imgRef} src={imageUrl} className="manga-img" />

      <canvas ref={canvasRef} className="mask-canvas" />

      <div className="text-layer">
        {panels.map((panel, pIdx) => (
          <React.Fragment key={pIdx}>
            
            {/* Bubbles (use shared font) */}
            {panel.bubbles?.map((b, bIdx) => {
              const ref = useBubbleFont();
              return (
                <div
                  key={`bubble-${pIdx}-${bIdx}`}
                  className="bubble-text"
                  style={{
                    ...boxStyle(b.bbox),
                    // Fixed padding for bubbles
                    padding: "4px",
                  }}
                >
                  <div className="text-inner" ref={ref}>
                    {b.en}
                  </div>
                </div>
              );
            })}

            {/* Outside text (independent font sizes) */}
            {panel.outside_text?.map((t, tIdx) => {
              const key = `${pIdx}-${tIdx}`;
              
              // Calculate dynamic padding based on the reserved 15% space (1 - 0.85 = 0.15)
              const [x1, y1, x2, y2] = t.bbox;
              const boxW = (x2 - x1) * scale;
              const boxH = (y2 - y1) * scale;

              const paddingFactor = 0.85;
              const paddingPercent = (1 - paddingFactor) / 2; // 0.075 or 7.5%
              
              const paddingX = boxW * paddingPercent; 
              const paddingY = boxH * paddingPercent;

              return (
                <div
                  key={`out-${pIdx}-${tIdx}`}
                  className="outside-text"
                  style={{
                    ...boxStyle(t.bbox),
                    fontSize: `${outsideFontSizes[key] || 14}px`, 
                    lineHeight: "1.15",
                    // Apply dynamic padding
                    padding: `${paddingY}px ${paddingX}px`, 
                  }}
                >
                  {t.en}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>

      {/* debug rectangles */}
      {debug && (
        <div className="debug-layer">
          {panels.map((panel, pIdx) => (
            <React.Fragment key={pIdx}>
              {panel.bubbles?.map((b, i) => (
                <div
                  key={`dbg-b-${pIdx}-${i}`}
                  className="debug-box"
                  style={boxStyle(b.bbox)}
                />
              ))}
              {panel.outside_text?.map((t, j) => (
                <div
                  key={`dbg-t-${pIdx}-${j}`}
                  className="debug-box outside"
                  style={boxStyle(t.bbox)}
                />
              ))}
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}