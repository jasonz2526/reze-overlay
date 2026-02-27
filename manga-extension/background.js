async function getSavedMode() {
  const result = await chrome.storage.sync.get({ translationMode: "simple" });
  return result.translationMode === "deep" ? "deep" : "simple";
}

async function sendStartCaptureToTab(tabId, mode) {
  if (!tabId) throw new Error("No active tab id available");

  await chrome.tabs.sendMessage(tabId, {
    action: "START_CAPTURE",
    mode,
  });
}

async function sendStartCaptureToActiveTab(mode) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return sendStartCaptureToTab(tab?.id, mode);
}

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "capture-manga") return;
  const mode = await getSavedMode();
  try {
    await sendStartCaptureToActiveTab(mode);
  } catch (err) {
    console.warn("Could not start capture from shortcut:", err);
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action === "START_CAPTURE_FROM_POPUP") {
    const mode = msg.mode === "deep" ? "deep" : "simple";
    const targetTabId = msg.tabId || sender?.tab?.id;

    (targetTabId
      ? sendStartCaptureToTab(targetTabId, mode)
      : sendStartCaptureToActiveTab(mode)
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
});
