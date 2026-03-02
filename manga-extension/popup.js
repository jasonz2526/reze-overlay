const modeInputs = Array.from(document.querySelectorAll('input[name="mode"]'));
const startBtn = document.getElementById("startCaptureBtn");
const autoRecaptureToggle = document.getElementById("autoRecaptureToggle");

function getSelectedMode() {
  const checked = modeInputs.find((input) => input.checked);
  return checked?.value === "deep" ? "deep" : "simple";
}

async function restoreSettings() {
  const { translationMode = "simple", autoRecaptureOnArrow = false } = await chrome.storage.sync.get({
    translationMode: "simple",
    autoRecaptureOnArrow: false,
  });

  modeInputs.forEach((input) => {
    input.checked = input.value === translationMode;
  });

  if (autoRecaptureToggle) {
    autoRecaptureToggle.checked = Boolean(autoRecaptureOnArrow);
  }
}

async function startCapture() {
  const mode = getSelectedMode();
  const autoRecaptureOnArrow = Boolean(autoRecaptureToggle?.checked);
  await chrome.storage.sync.set({ translationMode: mode, autoRecaptureOnArrow });

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  chrome.runtime.sendMessage(
    { action: "START_CAPTURE_FROM_POPUP", mode, tabId: tab?.id, autoRecaptureOnArrow },
    (response) => {
      if (chrome.runtime.lastError) {
        console.warn("Popup start capture error:", chrome.runtime.lastError.message);
        return;
      }

      if (!response?.ok) {
        console.warn("Popup start capture failed:", response?.error || "unknown");
        return;
      }

      window.close();
    }
  );
}

async function updateTranslationModeSetting() {
  const mode = getSelectedMode();
  await chrome.storage.sync.set({ translationMode: mode });
}

async function updateAutoRecaptureSetting() {
  const autoRecaptureOnArrow = Boolean(autoRecaptureToggle?.checked);
  await chrome.storage.sync.set({ autoRecaptureOnArrow });

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  chrome.runtime.sendMessage({
    action: "UPDATE_CAPTURE_SETTINGS_FROM_POPUP",
    tabId: tab?.id,
    autoRecaptureOnArrow,
  });
}

restoreSettings();
startBtn.addEventListener("click", startCapture);
modeInputs.forEach((input) =>
  input.addEventListener("change", updateTranslationModeSetting)
);
autoRecaptureToggle?.addEventListener("change", updateAutoRecaptureSetting);
