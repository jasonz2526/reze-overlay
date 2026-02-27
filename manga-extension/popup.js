const modeInputs = Array.from(document.querySelectorAll('input[name="mode"]'));
const startBtn = document.getElementById("startCaptureBtn");

function getSelectedMode() {
  const checked = modeInputs.find((input) => input.checked);
  return checked?.value === "deep" ? "deep" : "simple";
}

async function restoreMode() {
  const { translationMode = "simple" } = await chrome.storage.sync.get({
    translationMode: "simple",
  });

  modeInputs.forEach((input) => {
    input.checked = input.value === translationMode;
  });
}

async function startCapture() {
  const mode = getSelectedMode();
  await chrome.storage.sync.set({ translationMode: mode });

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  chrome.runtime.sendMessage(
    { action: "START_CAPTURE_FROM_POPUP", mode, tabId: tab?.id },
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

restoreMode();
startBtn.addEventListener("click", startCapture);
