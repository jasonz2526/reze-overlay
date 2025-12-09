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

  const [scale, setScale] = useState(0); // Initialize at 0 to prevent early calcs
  const [globalFontSize, setGlobalFontSize] = useState(16); // Default fallback
  const [outsideFontSizes, setOutsideFontSizes] = useState({});

  // 1. Compute scale based on the rendered image
  useEffect(() => {
    const updateScale = () => {
      if (!containerRef.current || !imgRef.current) return;
      const containerWidth = containerRef.current.clientWidth;
      const naturalWidth = imgRef.current.naturalWidth;
      if (naturalWidth > 0) {
        setScale(containerWidth / naturalWidth);
      }
    };
    
    // Initial check
    if (imgRef.current && imgRef.current.complete) {
        updateScale();
    }
    
    // Listener for load and resize
    const imgEl = imgRef.current;
    imgEl.addEventListener('load', updateScale);
    window.addEventListener("resize", updateScale);

    return () => {
        imgEl.removeEventListener('load', updateScale);
        window.removeEventListener("resize", updateScale);
    }
  }, [imageUrl]);

  // 2. Draw bubble + outside masks on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const img = imgRef.current;

    if (!canvas || !ctx || !img || !scale) return;

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

  // Helper: Draw Ellipse
  const drawBubbleMask = (ctx, bbox, scale) => {
    const [x1, y1, x2, y2] = bbox;
    const w = (x2 - x1) * scale;
    const h = (y2 - y1) * scale;
    const cx = (x1 * scale) + w / 2;
    const cy = (y1 * scale) + h / 2;

    ctx.save();
    ctx.fillStyle = "white";
    ctx.beginPath();
    // 0.94 factor brings the mask in slightly so borders don't get clipped
    ctx.ellipse(cx, cy, (w / 2) * 0.94, (h / 2) * 0.94, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  };

  // Helper: Draw Rect
  const drawOutsideMask = (ctx, bbox, scale) => {
    const [x1, y1, x2, y2] = bbox;
    ctx.save();
    ctx.fillStyle = "rgba(255,255,255,0.95)";
    ctx.fillRect(x1 * scale, y1 * scale, (x2 - x1) * scale, (y2 - y1) * scale);
    ctx.restore();
  };

  /**
   * CORE LOGIC: Compute Max Fitting Font Size
   * Uses a hidden DOM element to test wrap capability.
   */
  const calculateMaxFit = (text, width, height, padding = 20) => {
    // 1. Safety checks
    if (!text || width <= 0 || height <= 0) return 10;

    const availableW = width - (padding * 2);
    const availableH = height - (padding * 2);

    // If the box is impossibly small, return min size immediately
    if (availableW < 10 || availableH < 10) return 5;

    const tester = document.createElement("div");
    
    // 2. Exact CSS mirroring
    tester.style.position = "absolute";
    tester.style.visibility = "hidden";
    tester.style.fontFamily = "'aa', sans-serif"; 
    tester.style.fontWeight = "600";
    tester.style.lineHeight = "1.15";
    tester.style.boxSizing = "border-box";
    tester.style.width = `${availableW}px`; // Hard constraint on width
    tester.style.padding = "0"; 

    // 3. Force word breaking
    tester.style.whiteSpace = "normal";
    tester.style.overflowWrap = "anywhere"; 
    tester.style.wordBreak = "break-word"; 
    tester.style.hyphens = "auto";
    tester.style.letterSpacing = "-0.02em";

    tester.innerText = text;
    document.body.appendChild(tester);

    let low = 6; 
    let high = 30; 
    let bestFit = 6;

    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      tester.style.fontSize = `${mid}px`;

      // We trust CSS 'overflow-wrap' to handle the Width constraint.
      // Checking scrollWidth often triggers false negatives due to sub-pixel rendering.
      if (tester.scrollHeight <= availableH) {
        bestFit = mid; // Store this as the current candidate.
        low = mid + 1; // Try to go bigger.
      } else {
        high = mid - 1; // Too big, go smaller.
      }
    }

    document.body.removeChild(tester);
    return bestFit;
};

  // 3. Calculate Font Sizes
  useEffect(() => {
    if (!scale || panels.length === 0) return;

    const FONT_FAMILY = "'aa', sans-serif";

    // Part A: Calculate Bubble Sizes
    // We want the font size to be consistent, but small enough to fit the "tightest" bubble.
    let minCalculatedSize = 100; // Start high

    panels.forEach((panel) => {
      panel.bubbles?.forEach((b) => {
        const [x1, y1, x2, y2] = b.bbox;
        const w = (x2 - x1) * scale;
        const h = (y2 - y1) * scale;
        
        // Compute best fit for THIS specific bubble
        // Note: passing 4 as padding because CSS has padding: 4px
        const bestFit = calculateMaxFit(b.en, w, h, 4);
        
        // Track the smallest size found across all bubbles
        if (bestFit < minCalculatedSize) {
          minCalculatedSize = bestFit;
        }
      });
    });

    // Clamp the result to reasonable bounds (e.g., don't go below 11px, don't go above 22px)
    const finalGlobalSize = Math.max(5, Math.min(minCalculatedSize, 22));

    console.log(finalGlobalSize)
    setGlobalFontSize(finalGlobalSize);


    // Part B: Calculate Outside Text Sizes (Independent)
    const newOutsideSizes = {};
    const paddingFactor = 0.85;

    panels.forEach((panel, pIdx) => {
      panel.outside_text?.forEach((t, tIdx) => {
        const [x1, y1, x2, y2] = t.bbox;
        const boxW = (x2 - x1) * scale;
        const boxH = (y2 - y1) * scale;
        
        // Outside text uses percentage padding logic in your render, 
        // so we calculate available space similarly
        const usableW = boxW * paddingFactor;
        const usableH = boxH * paddingFactor;

        newOutsideSizes[`${pIdx}-${tIdx}`] = calculateMaxFit(t.en, usableW, usableH, 0);
      });
    });

    setOutsideFontSizes(newOutsideSizes);

  }, [scale, panels]);


  // Helper: CSS for boxes
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
      textAlign: "center",
      boxSizing: "border-box",
    };
  };

  return (
    <div ref={containerRef} className="manga-container">
      <img ref={imgRef} src={imageUrl} className="manga-img" alt="manga page" />
      <canvas ref={canvasRef} className="mask-canvas" />

      <div className="text-layer">
        {panels.map((panel, pIdx) => (
          <React.Fragment key={pIdx}>
            
            {/* Bubbles - Using Global "Minimum Necessary" Font Size */}
            {panel.bubbles?.map((b, bIdx) => (
              <div
                key={`bubble-${pIdx}-${bIdx}`}
                className="bubble-text"
                style={{
                  ...boxStyle(b.bbox),
                  fontSize: `${globalFontSize}px`,
                  padding: "4px", // Matches logic in calculateMaxFit
                }}
              >
                {b.en}
              </div>
            ))}

            {/* Outside Text - Independent Sizes */}
            {panel.outside_text?.map((t, tIdx) => {
              const key = `${pIdx}-${tIdx}`;
              const [x1, y1, x2, y2] = t.bbox;
              const boxW = (x2 - x1) * scale;
              const boxH = (y2 - y1) * scale;
              const paddingFactor = 0.85;
              const paddingPercent = (1 - paddingFactor) / 2;
              const paddingX = boxW * paddingPercent; 
              const paddingY = boxH * paddingPercent;

              return (
                <div
                  key={`out-${pIdx}-${tIdx}`}
                  className="outside-text"
                  style={{
                    ...boxStyle(t.bbox),
                    fontSize: `${outsideFontSizes[key] || 12}px`,
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

      {debug && (
        <div className="debug-layer">
          {panels.map((panel, pIdx) => (
            <React.Fragment key={pIdx}>
              {panel.bubbles?.map((b, i) => (
                <div key={`d-b-${pIdx}-${i}`} className="debug-box" style={boxStyle(b.bbox)} />
              ))}
              {panel.outside_text?.map((t, j) => (
                <div key={`d-t-${pIdx}-${j}`} className="debug-box outside" style={boxStyle(t.bbox)} />
              ))}
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}