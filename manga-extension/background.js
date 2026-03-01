async function getSavedCaptureSettings() {
  const result = await chrome.storage.sync.get({
    translationMode: "simple",
    autoRecaptureOnArrow: false,
  });

  return {
    mode: result.translationMode === "deep" ? "deep" : "simple",
    autoRecaptureOnArrow: Boolean(result.autoRecaptureOnArrow),
  };
}

async function sendStartCaptureToTab(tabId, mode, autoRecaptureOnArrow = false) {
  if (!tabId) throw new Error("No active tab id available");

  await chrome.tabs.sendMessage(tabId, {
    action: "START_CAPTURE",
    mode,
    autoRecaptureOnArrow,
  });
}

async function sendStartCaptureToActiveTab(mode, autoRecaptureOnArrow = false) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return sendStartCaptureToTab(tab?.id, mode, autoRecaptureOnArrow);
}

chrome.commands.onCommand.addListener(async (command) => {
  const { mode: savedMode, autoRecaptureOnArrow } = await getSavedCaptureSettings();
  let mode = savedMode;

  if (command === "capture-manga-simple") mode = "simple";
  else if (command === "capture-manga-deep") mode = "deep";
  else if (command !== "capture-manga") return;

  try {
    await sendStartCaptureToActiveTab(mode, autoRecaptureOnArrow);
  } catch (err) {
    console.warn("Could not start capture from shortcut:", err);
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action === "START_CAPTURE_FROM_POPUP") {
    const mode = msg.mode === "deep" ? "deep" : "simple";
    const autoRecaptureOnArrow = Boolean(msg.autoRecaptureOnArrow);
    const targetTabId = msg.tabId || sender?.tab?.id;

    (targetTabId
      ? sendStartCaptureToTab(targetTabId, mode, autoRecaptureOnArrow)
      : sendStartCaptureToActiveTab(mode, autoRecaptureOnArrow)
    )
      .then(() => sendResponse({ ok: true }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (msg?.action === "CAPTURE_SCREEN") {
    chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
      sendResponse({ screenshot: dataUrl });
    });
    return true;
  }

  if (msg?.action === "UPDATE_CAPTURE_SETTINGS_FROM_POPUP") {
    const targetTabId = msg.tabId || sender?.tab?.id;
    const autoRecaptureOnArrow = Boolean(msg.autoRecaptureOnArrow);

    if (!targetTabId) {
      sendResponse({ ok: false, error: "No active tab id available" });
      return false;
    }

    chrome.tabs
      .sendMessage(targetTabId, {
        action: "UPDATE_CAPTURE_SETTINGS",
        autoRecaptureOnArrow,
      })
      .then(() => sendResponse({ ok: true }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }
});
