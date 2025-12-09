chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action === "CAPTURE_SCREEN") {
      chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
        sendResponse({ screenshot: dataUrl });
      });
  
      // Keep channel open
      return true;
    }
  });
  