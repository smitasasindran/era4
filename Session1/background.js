// Background service worker for handling keyboard shortcuts
chrome.commands.onCommand.addListener((command) => {
  if (command === "take-screenshot") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].url.includes("youtube.com")) {
        chrome.tabs.sendMessage(tabs[0].id, { action: "takeScreenshot" });
      }
    });
  } else if (command === "bookmark-timestamp") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].url.includes("youtube.com")) {
        chrome.tabs.sendMessage(tabs[0].id, { action: "bookmarkTimestamp" });
      }
    });
  }
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "saveScreenshot") {
    // Save screenshot data to storage
    chrome.storage.local.get(['screenshots'], (result) => {
      const screenshots = result.screenshots || [];
      screenshots.push({
        id: Date.now(),
        timestamp: request.timestamp,
        videoId: request.videoId,
        videoTitle: request.videoTitle,
        screenshot: request.screenshot,
        date: new Date().toISOString()
      });
      chrome.storage.local.set({ screenshots: screenshots });
    });
    sendResponse({ success: true });
  } else if (request.action === "saveBookmark") {
    // Save bookmark data to storage
    chrome.storage.local.get(['bookmarks'], (result) => {
      const bookmarks = result.bookmarks || [];
      bookmarks.push({
        id: Date.now(),
        timestamp: request.timestamp,
        videoId: request.videoId,
        videoTitle: request.videoTitle,
        transcript: request.transcript,
        date: new Date().toISOString()
      });
      chrome.storage.local.set({ bookmarks: bookmarks });
    });
    sendResponse({ success: true });
  }
  return true;
});
