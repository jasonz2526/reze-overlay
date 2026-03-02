// contentScript.js

(function () {
  // Avoid double injection
  if (document.getElementById("manga-overlay-root")) return;

  // Inject extension-scoped font-face so URL resolution never depends on page origin.
  const fontStyle = document.createElement("style");
  fontStyle.id = "manga-overlay-font-style";
  fontStyle.textContent = `
    @font-face {
      font-family: "aa";
      src: url("${chrome.runtime.getURL("fonts/animeace2_reg.woff2")}") format("woff2"),
           url("${chrome.runtime.getURL("fonts/animeace2_reg.otf")}") format("opentype");
      font-weight: 400;
      font-style: normal;
    }
  `;
  document.documentElement.appendChild(fontStyle);

  // Create a container for React
  const root = document.createElement("div");
  root.id = "manga-overlay-root";

  // Full-page overlay root; app will toggle pointer events while selecting.
  Object.assign(root.style, {
    position: "absolute",
    top: "0",
    left: "0",
    width: "100%",
    height: "100%",
    pointerEvents: "none",
    zIndex: "999999",
  });

  document.documentElement.appendChild(root);

  // Inject the React bundle
  const script = document.createElement("script");
  script.src = chrome.runtime.getURL("overlay.js");
  script.type = "module";
  document.documentElement.appendChild(script);
})();

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.action === "START_CAPTURE") {
    window.dispatchEvent(
      new CustomEvent("reze-overlay:start-capture", {
        detail: {
          mode: msg.mode === "deep" ? "deep" : "simple",
          autoRecaptureOnArrow: Boolean(msg.autoRecaptureOnArrow),
        },
      })
    );

    sendResponse({ ok: true });
    return;
  }

  if (msg?.action === "UPDATE_CAPTURE_SETTINGS") {
    window.dispatchEvent(
      new CustomEvent("reze-overlay:update-settings", {
        detail: {
          autoRecaptureOnArrow: Boolean(msg.autoRecaptureOnArrow),
        },
      })
    );

    sendResponse({ ok: true });
  }
});

window.addEventListener("reze-overlay:capture-screen-request", (event) => {
  const requestId = event?.detail?.requestId;
  if (!requestId) return;

  chrome.runtime.sendMessage({ action: "CAPTURE_SCREEN" }, (response) => {
    const screenshot = response?.screenshot || null;

    window.dispatchEvent(
      new CustomEvent("reze-overlay:capture-screen-response", {
        detail: { requestId, screenshot },
      })
    );
  });
});
