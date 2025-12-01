// contentScript.js

(function () {
    // Avoid double injection
    if (document.getElementById("manga-overlay-root")) return;
  
    // Create a container for React
    const root = document.createElement("div");
    root.id = "manga-overlay-root";
  
    // Style: full-page overlay but non-blocking until you open your UI
    Object.assign(root.style, {
      position: "fixed",
      inset: "0",
      pointerEvents: "none",   // React UI can toggle this on when active
      zIndex: "999999"
    });
  
    document.documentElement.appendChild(root);
  
    // Inject the React bundle
    const script = document.createElement("script");
    script.src = chrome.runtime.getURL("overlay.js");
    script.type = "module";
    document.documentElement.appendChild(script);
  })();
  