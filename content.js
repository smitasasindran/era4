// Content script that runs on YouTube pages
let currentVideoId = null;
let currentVideoTitle = null;
let transcriptData = null;

// Initialize when page loads
function initialize() {
  // Extract video ID and title
  const urlParams = new URLSearchParams(window.location.search);
  currentVideoId = urlParams.get('v');
  
  const titleElement = document.querySelector('h1.ytd-video-primary-info-renderer');
  currentVideoTitle = titleElement ? titleElement.textContent.trim() : 'Unknown Video';
  
  // Try to get transcript data
  getTranscriptData();
  
  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "takeScreenshot") {
      takeScreenshot();
    } else if (request.action === "bookmarkTimestamp") {
      bookmarkTimestamp();
    } else if (request.action === "jumpToTimestamp") {
      jumpToTimestamp(request.timestamp);
    }
  });
  
  // Add visual feedback elements
  addVisualFeedback();
}

// Get transcript data from YouTube
async function getTranscriptData() {
  try {
    // Look for transcript button and click it to load transcripts
    const transcriptButton = document.querySelector('button[aria-label*="transcript"], button[aria-label*="Transcript"]');
    if (transcriptButton) {
      transcriptButton.click();
      
      // Wait for transcript to load
      setTimeout(() => {
        const transcriptItems = document.querySelectorAll('.ytd-transcript-segment-renderer');
        if (transcriptItems.length > 0) {
          transcriptData = Array.from(transcriptItems).map(item => {
            const timestamp = item.querySelector('.ytd-transcript-segment-renderer');
            const text = item.querySelector('.ytd-transcript-segment-text');
            return {
              timestamp: timestamp ? timestamp.textContent.trim() : '',
              text: text ? text.textContent.trim() : ''
            };
          });
        }
      }, 1000);
    }
  } catch (error) {
    console.log('Could not load transcript:', error);
  }
}

// Take screenshot of current video frame
async function takeScreenshot() {
  try {
    const video = document.querySelector('video');
    if (!video) {
      showNotification('No video found on page', 'error');
      return;
    }
    
    // Create canvas to capture video frame
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw current video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert to base64 data URL
    const screenshot = canvas.toDataURL('image/png');
    
    // Get current timestamp
    const timestamp = formatTime(video.currentTime);
    
    // Save screenshot
    chrome.runtime.sendMessage({
      action: "saveScreenshot",
      timestamp: timestamp,
      videoId: currentVideoId,
      videoTitle: currentVideoTitle,
      screenshot: screenshot
    }, (response) => {
      if (response && response.success) {
        showNotification(`Screenshot saved at ${timestamp}`, 'success');
      }
    });
    
  } catch (error) {
    console.error('Error taking screenshot:', error);
    showNotification('Error taking screenshot', 'error');
  }
}

// Bookmark current timestamp with transcript
async function bookmarkTimestamp() {
  try {
    const video = document.querySelector('video');
    if (!video) {
      showNotification('No video found on page', 'error');
      return;
    }
    
    const currentTime = video.currentTime;
    const timestamp = formatTime(currentTime);
    
    // Get transcript around current time (10 seconds before and after)
    let transcript = '';
    if (transcriptData) {
      const relevantTranscripts = transcriptData.filter(item => {
        const itemTime = parseTime(item.timestamp);
        return itemTime >= currentTime - 10 && itemTime <= currentTime + 10;
      });
      
      transcript = relevantTranscripts.map(item => `${item.timestamp}: ${item.text}`).join('\n');
    }
    
    if (!transcript) {
      transcript = 'No transcript available for this timestamp';
    }
    
    // Save bookmark
    chrome.runtime.sendMessage({
      action: "saveBookmark",
      timestamp: timestamp,
      videoId: currentVideoId,
      videoTitle: currentVideoTitle,
      transcript: transcript
    }, (response) => {
      if (response && response.success) {
        showNotification(`Bookmark saved at ${timestamp}`, 'success');
      }
    });
    
  } catch (error) {
    console.error('Error bookmarking timestamp:', error);
    showNotification('Error bookmarking timestamp', 'error');
  }
}

// Helper function to format time in MM:SS format
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Helper function to parse timestamp string to seconds
function parseTime(timeString) {
  const parts = timeString.split(':').map(Number);
  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  } else if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  return 0;
}

// Jump to specific timestamp in the video
function jumpToTimestamp(timestamp) {
  const video = document.querySelector('video');
  if (!video) {
    showNotification('No video found on page', 'error');
    return;
  }
  
  const seconds = parseTime(timestamp);
  if (seconds >= 0) {
    // Add a small delay to ensure video is ready
    setTimeout(() => {
      video.currentTime = seconds;
      showNotification(`Jumped to ${timestamp}`, 'success');
      
      // Scroll video into view if needed
      video.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Pause video at the timestamp for better viewing
      if (!video.paused) {
        video.pause();
      }
    }, 100);
  } else {
    showNotification('Invalid timestamp format', 'error');
  }
}

// Add visual feedback elements
function addVisualFeedback() {
  // Create notification container
  const notificationContainer = document.createElement('div');
  notificationContainer.id = 'youtube-notes-notifications';
  notificationContainer.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    pointer-events: none;
  `;
  document.body.appendChild(notificationContainer);
  
  // Create floating action buttons
  const actionButtons = document.createElement('div');
  actionButtons.id = 'youtube-notes-actions';
  actionButtons.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 10000;
    display: flex;
    flex-direction: column;
    gap: 10px;
  `;
  
  const screenshotBtn = document.createElement('button');
  screenshotBtn.textContent = '📸 Screenshot';
  screenshotBtn.style.cssText = `
    padding: 10px 15px;
    background: #ff0000;
    color: white;
    border: none;
    border-radius: 25px;
    cursor: pointer;
    font-size: 14px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
  `;
  screenshotBtn.onclick = takeScreenshot;
  
  const bookmarkBtn = document.createElement('button');
  bookmarkBtn.textContent = '🔖 Bookmark';
  bookmarkBtn.style.cssText = `
    padding: 10px 15px;
    background: #2196F3;
    color: white;
    border: none;
    border-radius: 25px;
    cursor: pointer;
    font-size: 14px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
  `;
  bookmarkBtn.onclick = bookmarkTimestamp;
  
  actionButtons.appendChild(screenshotBtn);
  actionButtons.appendChild(bookmarkBtn);
  document.body.appendChild(actionButtons);
}

// Show notification
function showNotification(message, type = 'info') {
  const notificationContainer = document.getElementById('youtube-notes-notifications');
  if (!notificationContainer) return;
  
  const notification = document.createElement('div');
  notification.style.cssText = `
    background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
    color: white;
    padding: 12px 20px;
    border-radius: 5px;
    margin-bottom: 10px;
    font-size: 14px;
    max-width: 300px;
    word-wrap: break-word;
    animation: slideIn 0.3s ease-out;
  `;
  notification.textContent = message;
  
  notificationContainer.appendChild(notification);
  
  // Remove notification after 3 seconds
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-in';
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 300);
  }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  
  @keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
  }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}

// Re-initialize when navigating to different videos
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    setTimeout(initialize, 1000); // Wait for page to load
  }
}).observe(document, { subtree: true, childList: true });
