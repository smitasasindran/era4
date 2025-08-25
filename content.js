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
  
  // Also try to load any previously saved local transcript
  loadSavedTranscript();
  
  // Try to detect existing transcripts on the page
  setTimeout(() => {
    checkForExistingTranscripts();
  }, 2000);
  
  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "takeScreenshot") {
      takeScreenshot();
    } else if (request.action === "bookmarkTimestamp") {
      bookmarkTimestamp();
    } else if (request.action === "jumpToTimestamp") {
      jumpToTimestamp(request.timestamp);
    } else if (request.action === "updateTranscriptData") {
      transcriptData = request.transcriptData;
      showNotification(`Transcript updated with ${transcriptData.length} segments`, 'success');
    }
  });
  
  // Add a button to manually refresh transcript data
  addTranscriptRefreshButton();
  
  // Add visual feedback elements
  addVisualFeedback();
}

// Get transcript data from YouTube
async function getTranscriptData() {
  try {
    console.log('Attempting to find transcript button...');
    
    // Look for transcript button with multiple possible selectors
    let transcriptButton = document.querySelector('button[aria-label*="transcript"], button[aria-label*="Transcript"], button[aria-label*="Show transcript"], button[aria-label*="Open transcript"]');
    
    if (!transcriptButton) {
      // Try alternative selectors for transcript button
      transcriptButton = document.querySelector('[aria-label*="transcript"], [aria-label*="Transcript"], [aria-label*="Show transcript"], [aria-label*="Open transcript"]');
    }
    
    if (!transcriptButton) {
      // Try looking for transcript in the more actions menu
      const moreActionsButton = document.querySelector('button[aria-label*="More actions"], button[aria-label*="More"], button[aria-label*="..."]');
      if (moreActionsButton) {
        console.log('Found more actions button, checking for transcript option...');
        moreActionsButton.click();
        setTimeout(() => {
          const transcriptOption = document.querySelector('[aria-label*="transcript"], [aria-label*="Transcript"]');
          if (transcriptOption) {
            console.log('Found transcript option in more actions menu');
            transcriptOption.click();
            setTimeout(() => {
              extractTranscriptData();
            }, 1000);
          }
        }, 500);
        return;
      }
    }
    
    if (transcriptButton) {
      console.log('Found transcript button, clicking...');
      transcriptButton.click();
      
      // Wait for transcript to load and then extract data
      setTimeout(() => {
        extractTranscriptData();
      }, 1500);
    } else {
      console.log('Transcript button not found - trying alternative approach...');
      // Try to find transcript panel that might already be open
      setTimeout(() => {
        extractTranscriptData();
      }, 1000);
    }
  } catch (error) {
    console.log('Could not load transcript:', error);
  }
}

// Extract transcript data from the loaded transcript panel
function extractTranscriptData() {
  try {
    console.log('Extracting transcript data...');
    
    // Look for transcript segments in different possible selectors
    let transcriptItems = document.querySelectorAll('.ytd-transcript-segment-renderer, [data-segment-start-time], .ytd-transcript-segment-text');
    
    if (transcriptItems.length === 0) {
      // Try alternative selectors for YouTube transcripts
      transcriptItems = document.querySelectorAll('[data-segment-start-time], .ytd-transcript-segment-text, .ytd-transcript-segment-content');
    }
    
    if (transcriptItems.length === 0) {
      // Try looking for transcript panel that might already be open
      const transcriptPanel = document.querySelector('ytd-transcript-renderer, .ytd-transcript-renderer');
      if (transcriptPanel) {
        console.log('Found transcript panel, looking for segments...');
        transcriptItems = transcriptPanel.querySelectorAll('[data-segment-start-time], .ytd-transcript-segment-text, .ytd-transcript-segment-content');
      }
    }
    
    if (transcriptItems.length === 0) {
      // Try one more approach - look for any elements with transcript-like content
      const allElements = document.querySelectorAll('*');
      transcriptItems = Array.from(allElements).filter(el => {
        const text = el.textContent || '';
        const hasTimestamp = /\d{1,2}:\d{2}/.test(text);
        const hasText = text.length > 10 && text.length < 200;
        return hasTimestamp && hasText && el.children.length === 0;
      });
    }
    
    if (transcriptItems.length > 0) {
      console.log(`Found ${transcriptItems.length} potential transcript items`);
      
      transcriptData = Array.from(transcriptItems).map(item => {
        // Try to get timestamp from data attribute first
        let timestamp = item.getAttribute('data-segment-start-time');
        let text = '';
        
        if (!timestamp) {
          // Fallback to looking for timestamp element
          const timestampElement = item.querySelector('[data-segment-start-time], .ytd-transcript-segment-timestamp');
          if (timestampElement) {
            timestamp = timestampElement.textContent.trim();
          }
        }
        
        // If still no timestamp, try to extract from text content
        if (!timestamp) {
          const textContent = item.textContent || '';
          const timeMatch = textContent.match(/(\d{1,2}:\d{2})/);
          if (timeMatch) {
            timestamp = timeMatch[1];
            text = textContent.replace(timeMatch[0], '').trim();
          }
        }
        
        // Get text content if not already extracted
        if (!text) {
          const textElement = item.querySelector('.ytd-transcript-segment-text, .ytd-transcript-segment-content');
          if (textElement) {
            text = textElement.textContent.trim();
          } else {
            text = item.textContent.trim();
          }
        }
        
        // Convert timestamp to seconds if it's a number
        if (timestamp && !isNaN(timestamp)) {
          timestamp = formatTime(parseFloat(timestamp));
        }
        
        return {
          timestamp: timestamp || '',
          text: text || '',
          seconds: timestamp ? parseTime(timestamp) : 0
        };
      }).filter(item => item.text && item.timestamp && item.text.length > 5); // Only keep items with both text and timestamp
      
      console.log('Transcript data extracted:', transcriptData.length, 'segments');
      
      if (transcriptData.length > 0) {
        showNotification(`Found ${transcriptData.length} transcript segments`, 'success');
        console.log('Transcript data:', transcriptData);
      }
    } else {
      console.log('No transcript segments found');
    }
  } catch (error) {
    console.log('Error extracting transcript data:', error);
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
    
    // Get transcript around current time (10 seconds before and 20 seconds after)
    let transcript = '';
    let relevantTranscripts = [];
    
    if (transcriptData && transcriptData.length > 0) {
      relevantTranscripts = transcriptData.filter(item => {
        // Use the seconds property if available, otherwise parse the timestamp
        const itemTime = item.seconds || parseTime(item.timestamp);
        return itemTime >= currentTime - 10 && itemTime <= currentTime + 20;
      });
      
      if (relevantTranscripts.length > 0) {
        // Sort by time and format nicely
        relevantTranscripts.sort((a, b) => (a.seconds || parseTime(a.timestamp)) - (b.seconds || parseTime(b.timestamp)));
        
        transcript = relevantTranscripts.map(item => {
          const time = item.timestamp || formatTime(item.seconds || parseTime(item.timestamp));
          return `${time}: ${item.text}`;
        }).join('\n');
        
        console.log(`Found ${relevantTranscripts.length} transcript segments around timestamp ${timestamp}`);
        console.log('Relevant transcripts:', relevantTranscripts);
      }
    }
    
    if (!transcript) {
      transcript = 'No transcript available for this timestamp';
    }
    
    // Save bookmark (always save, even without transcript)
    chrome.runtime.sendMessage({
      action: "saveBookmark",
      timestamp: timestamp,
      videoId: currentVideoId,
      videoTitle: currentVideoTitle,
      transcript: transcript
    }, (response) => {
      if (response && response.success) {
        if (relevantTranscripts.length > 0) {
          showNotification(`Bookmark saved at ${timestamp} with ${relevantTranscripts.length} transcript segments`, 'success');
        } else {
          showNotification(`Bookmark saved at ${timestamp} (no transcript available)`, 'success');
        }
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

// Upload local transcript file
function uploadLocalTranscript() {
  // Create a hidden file input
  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = '.txt,.srt,.vtt,.json';
  fileInput.style.display = 'none';
  
  fileInput.onchange = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const content = e.target.result;
          parseLocalTranscript(content, file.name);
        } catch (error) {
          showNotification('Error reading transcript file', 'error');
          console.error('Error reading file:', error);
        }
      };
      reader.readAsText(file);
    }
  };
  
  document.body.appendChild(fileInput);
  fileInput.click();
  document.body.removeChild(fileInput);
}

// Parse uploaded transcript file
function parseLocalTranscript(content, filename) {
  try {
    let parsedTranscript = [];
    
    // Try to detect file format and parse accordingly
    if (filename.endsWith('.srt')) {
      parsedTranscript = parseSRTFile(content);
    } else if (filename.endsWith('.vtt')) {
      parsedTranscript = parseVTTFile(content);
    } else if (filename.endsWith('.json')) {
      parsedTranscript = parseJSONTranscript(content);
    } else {
      // Assume it's a plain text file with timestamps
      parsedTranscript = parsePlainTextTranscript(content);
    }
    
    if (parsedTranscript.length > 0) {
      transcriptData = parsedTranscript;
      
      // Save transcript data to local storage for persistence
      chrome.storage.local.set({ 
        [`transcript_${currentVideoId}`]: {
          data: parsedTranscript,
          filename: filename,
          date: new Date().toISOString()
        }
      });
      
      showNotification(`Successfully loaded ${parsedTranscript.length} transcript segments from ${filename}`, 'success');
      console.log('Local transcript loaded:', parsedTranscript);
    } else {
      showNotification('No valid transcript data found in file', 'warning');
    }
  } catch (error) {
    showNotification('Error parsing transcript file', 'error');
    console.error('Error parsing transcript:', error);
  }
}

// Parse SRT subtitle file
function parseSRTFile(content) {
  const segments = [];
  const blocks = content.split('\n\n').filter(block => block.trim());
  
  for (const block of blocks) {
    const lines = block.split('\n').filter(line => line.trim());
    if (lines.length >= 3) {
      const timeLine = lines[1];
      const text = lines.slice(2).join(' ').trim();
      
      // Parse SRT timestamp format (00:00:00,000 --> 00:00:00,000)
      const timeMatch = timeLine.match(/(\d{2}):(\d{2}):(\d{2}),(\d{3})/);
      if (timeMatch) {
        const hours = parseInt(timeMatch[1]);
        const minutes = parseInt(timeMatch[2]);
        const seconds = parseInt(timeMatch[3]);
        const totalSeconds = hours * 3600 + minutes * 60 + seconds;
        const timestamp = formatTime(totalSeconds);
        
        segments.push({
          timestamp: timestamp,
          text: text,
          seconds: totalSeconds
        });
      }
    }
  }
  
  return segments;
}

// Parse VTT subtitle file
function parseVTTFile(content) {
  const segments = [];
  const lines = content.split('\n');
  let currentTime = '';
  let currentText = '';
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // Skip header lines
    if (line === 'WEBVTT' || line === '' || line.includes('-->')) {
      continue;
    }
    
    // Check if line contains timestamp
    const timeMatch = line.match(/(\d{2}):(\d{2}):(\d{2})\.(\d{3})/);
    if (timeMatch) {
      // Save previous segment if exists
      if (currentTime && currentText) {
        const totalSeconds = parseTime(currentTime);
        segments.push({
          timestamp: currentTime,
          text: currentText.trim(),
          seconds: totalSeconds
        });
      }
      
      currentTime = timeMatch[0];
      currentText = '';
    } else if (line && currentTime) {
      currentText += line + ' ';
    }
  }
  
  // Add last segment
  if (currentTime && currentText) {
    const totalSeconds = parseTime(currentTime);
    segments.push({
      timestamp: currentTime,
      text: currentText.trim(),
      seconds: totalSeconds
    });
  }
  
  return segments;
}

// Parse JSON transcript file
function parseJSONTranscript(content) {
  try {
    const data = JSON.parse(content);
    if (Array.isArray(data)) {
      return data.map(item => ({
        timestamp: item.timestamp || item.time || formatTime(item.seconds || 0),
        text: item.text || item.content || '',
        seconds: item.seconds || parseTime(item.timestamp || item.time || '0:00')
      }));
    } else if (data.segments || data.transcript) {
      const segments = data.segments || data.transcript;
      return segments.map(item => ({
        timestamp: item.timestamp || item.time || formatTime(item.seconds || 0),
        text: item.text || item.content || '',
        seconds: item.seconds || parseTime(item.timestamp || item.time || '0:00')
      }));
    }
  } catch (error) {
    console.error('Error parsing JSON:', error);
  }
  return [];
}

// Parse plain text transcript with timestamps
function parsePlainTextTranscript(content) {
  const segments = [];
  const lines = content.split('\n').filter(line => line.trim());
  
  for (const line of lines) {
    // Look for timestamp patterns like [00:00] or (00:00) or 00:00
    const timeMatch = line.match(/(?:\[|\()?(\d{1,2}):(\d{2})(?:\]|\))?\s*(.+)/);
    if (timeMatch) {
      const minutes = parseInt(timeMatch[1]);
      const seconds = parseInt(timeMatch[2]);
      const text = timeMatch[3].trim();
      const totalSeconds = minutes * 60 + seconds;
      const timestamp = formatTime(totalSeconds);
      
      segments.push({
        timestamp: timestamp,
        text: text,
        seconds: totalSeconds
      });
    }
  }
  
  return segments;
}

// Load previously saved transcript data
function loadSavedTranscript() {
  if (currentVideoId) {
    chrome.storage.local.get([`transcript_${currentVideoId}`], (result) => {
      const savedTranscript = result[`transcript_${currentVideoId}`];
      if (savedTranscript && savedTranscript.data) {
        transcriptData = savedTranscript.data;
        console.log(`Loaded saved transcript with ${transcriptData.length} segments from ${savedTranscript.filename}`);
        showNotification(`Loaded saved transcript: ${savedTranscript.filename}`, 'info');
      }
    });
  }
}

// Check for existing transcripts on the page
function checkForExistingTranscripts() {
  console.log('Checking for existing transcripts on the page...');
  
  // Look for transcript panel that might already be open
  const transcriptPanel = document.querySelector('ytd-transcript-renderer, .ytd-transcript-renderer, [data-segment-start-time]');
  if (transcriptPanel) {
    console.log('Found existing transcript panel, extracting data...');
    extractTranscriptData();
  } else {
    console.log('No existing transcript panel found');
  }
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

// Add transcript refresh button
function addTranscriptRefreshButton() {
  const actionButtons = document.getElementById('youtube-notes-actions');
  if (actionButtons) {
    const refreshBtn = document.createElement('button');
    refreshBtn.textContent = '🔄 Refresh Transcript';
    refreshBtn.style.cssText = `
      padding: 10px 15px;
      background: #4CAF50;
      color: white;
      border: none;
      border-radius: 25px;
      cursor: pointer;
      font-size: 14px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    `;
    refreshBtn.onclick = () => {
      showNotification('Refreshing transcript data...', 'info');
      getTranscriptData();
    };
    actionButtons.appendChild(refreshBtn);
    
    // Add manual transcript detection button
    const detectBtn = document.createElement('button');
    detectBtn.textContent = '🔍 Detect Transcript';
    detectBtn.style.cssText = `
      padding: 10px 15px;
      background: #9C27B0;
      color: white;
      border: none;
      border-radius: 25px;
      cursor: pointer;
      font-size: 14px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    `;
    detectBtn.onclick = () => {
      showNotification('Manually detecting transcript...', 'info');
      extractTranscriptData();
    };
    actionButtons.appendChild(detectBtn);
    
    // Add upload transcript button
    const uploadBtn = document.createElement('button');
    uploadBtn.textContent = '📁 Upload Transcript';
    uploadBtn.style.cssText = `
      padding: 10px 15px;
      background: #FF9800;
      color: white;
      border: none;
      border-radius: 25px;
      cursor: pointer;
      font-size: 14px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    `;
    uploadBtn.onclick = () => {
      uploadLocalTranscript();
    };
    actionButtons.appendChild(uploadBtn);
  }
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
