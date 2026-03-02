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
  const [bubbleFontSizes, setBubbleFontSizes] = useState({});
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
  const getTextFitProfile = (text) => {
    const cleaned = (text || "").trim();
    const words = cleaned ? cleaned.split(/\s+/) : [];
    const charCount = cleaned.replace(/\s+/g, "").length;
    const wordCount = words.length;
    const isSingleWord = wordCount === 1;
    const isShortPhrase = !isSingleWord && wordCount <= 3 && charCount <= 14;

    // Wrap profile:
    // - short text: avoid aggressive breaking/hyphenation
    // - long text: allow flexible wrapping for fit
    const wrap =
      isSingleWord || isShortPhrase
        ? {
            overflowWrap: "normal",
            wordBreak: "normal",
            hyphens: "none",
            letterSpacing: "0em",
          }
        : {
            overflowWrap: "anywhere",
            wordBreak: "break-word",
            hyphens: "auto",
            letterSpacing: "-0.02em",
          };

    // Line constraints:
    // - single-word bubbles should remain one line
    // - short phrases should generally be <= 2 lines
    let maxLines = null;
    if (isSingleWord) maxLines = 1;
    else if (isShortPhrase) maxLines = 2;

    return { isSingleWord, charCount, wrap, maxLines };
  };

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

    // 3. Dynamic wrap/line profile by text shape
    const profile = getTextFitProfile(text);
    tester.style.whiteSpace = "normal";
    tester.style.overflowWrap = profile.wrap.overflowWrap;
    tester.style.wordBreak = profile.wrap.wordBreak;
    tester.style.hyphens = profile.wrap.hyphens;
    tester.style.letterSpacing = profile.wrap.letterSpacing;

    tester.innerText = text;
    document.body.appendChild(tester);

    let low = 6; 
    let high = 30; 
    let bestFit = 6;

    // Single-word width cap to avoid oversized letter rendering.
    if (profile.isSingleWord && profile.charCount > 0) {
      const approxCharWidthFactor = 0.72;
      const singleWordCap = Math.floor(availableW / Math.max(1, profile.charCount * approxCharWidthFactor));
      high = Math.min(high, Math.max(8, singleWordCap));
    }

    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      tester.style.fontSize = `${mid}px`;

      const lineHeightPx = mid * 1.15;
      const lineCount = Math.max(1, Math.round(tester.scrollHeight / lineHeightPx));
      const withinHeight = tester.scrollHeight <= availableH;
      const withinLines = profile.maxLines == null || lineCount <= profile.maxLines;

      if (withinHeight && withinLines) {
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

    // Part A: Calculate Bubble Sizes (independent per bubble)
    // We shrink usable area a bit because bubble masks are elliptical.
    const newBubbleSizes = {};
    const bubblePaddingFactorW = 0.82;
    const bubblePaddingFactorH = 0.82;
    const maxTallHeightBonus = 0.10;

    panels.forEach((panel) => {
      panel.bubbles?.forEach((b, bIdx) => {
        const [x1, y1, x2, y2] = b.bbox;
        const boxW = (x2 - x1) * scale;
        const boxH = (y2 - y1) * scale;
        const aspectRatio = boxH / Math.max(boxW, 1);
        const tallness = Math.max(0, Math.min(aspectRatio - 1, 1));
        const usableW = boxW * bubblePaddingFactorW;
        const usableH = boxH * (bubblePaddingFactorH + tallness * maxTallHeightBonus);
        const fitted = calculateMaxFit(b.en, usableW, usableH, 0);
        const bubbleSizeNudge = tallness > 0.35 ? 0 : 1;
        const key = `${panel.panel_id ?? "p"}-${b.bubble_id ?? bIdx}`;

        newBubbleSizes[key] = (Math.max(5, Math.min(fitted, 22)) - bubbleSizeNudge) * 0.7;
      });
    });

    setBubbleFontSizes(newBubbleSizes);


    // Part B: Calculate Outside Text Sizes (Independent)
    const newOutsideSizes = {};
    const paddingFactor = 0.85;

    panels.forEach((panel, pIdx) => {
      panel.outside_text?.forEach((t, tIdx) => {
        const [x1, y1, x2, y2] = t.bbox;
        const boxW = (x2 - x1) * scale;
        const boxH = (y2 - y1) * scale;
        const profile = getTextFitProfile(t.en);
        
        // Outside text uses percentage padding logic in your render, 
        // so we calculate available space similarly
        const usableW = boxW * paddingFactor;
        const usableH = boxH * paddingFactor;
        const fitted = calculateMaxFit(t.en, usableW, usableH, 0);
        const nudge = profile.isSingleWord ? 0 : 1;
        newOutsideSizes[`${pIdx}-${tIdx}`] = Math.max(6, Math.min(fitted - nudge, 28));
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
            
            {/* Bubbles - Independent per bubble */}
            {panel.bubbles?.map((b, bIdx) => {
              const key = `${panel.panel_id ?? "p"}-${b.bubble_id ?? bIdx}`;
              const profile = getTextFitProfile(b.en);
              return (
                <div
                  key={`bubble-${pIdx}-${bIdx}`}
                  className="bubble-text"
                  style={{
                    ...boxStyle(b.bbox),
                    fontSize: `${bubbleFontSizes[key] || 12}px`,
                    padding: "4px", // Matches logic in calculateMaxFit
                    overflowWrap: profile.wrap.overflowWrap,
                    wordBreak: profile.wrap.wordBreak,
                    hyphens: profile.wrap.hyphens,
                    letterSpacing: profile.wrap.letterSpacing,
                  }}
                >
                  {b.en}
                </div>
              );
            })}

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
              const profile = getTextFitProfile(t.en);

              return (
                <div
                  key={`out-${pIdx}-${tIdx}`}
                  className="outside-text"
                  style={{
                    ...boxStyle(t.bbox),
                    fontSize: `${outsideFontSizes[key] || 12}px`,
                    padding: `${paddingY}px ${paddingX}px`,
                    overflowWrap: profile.wrap.overflowWrap,
                    wordBreak: profile.wrap.wordBreak,
                    hyphens: profile.wrap.hyphens,
                    letterSpacing: profile.wrap.letterSpacing,
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
