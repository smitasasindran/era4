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
  
  // Add visual feedback elements first (creates the button container)
  addVisualFeedback();
  
  // Then add transcript buttons to the container with a small delay
  setTimeout(() => {
    addTranscriptRefreshButton();
  }, 100);
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
      // Fallback: heuristic scan
      const allElements = document.querySelectorAll('*');
      transcriptItems = Array.from(allElements).filter(el => {
        const text = el.textContent || '';
        const hasTimestamp = /\b\d{1,2}:\d{2}(?::\d{2})?\b/.test(text);
        const hasText = text.length > 10 && text.length < 200;
        return hasTimestamp && hasText && el.children.length === 0;
      });
    }
    
    if (transcriptItems.length > 0) {
      console.log(`Found ${transcriptItems.length} potential transcript items`);
      
      const videoEl = document.querySelector('video');
      const videoDuration = videoEl && isFinite(videoEl.duration) ? videoEl.duration : NaN;
      
      // Build segments adaptively resolving 2-part timestamps (MM:SS vs HH:MM)
      const segments = [];
      let lastSeconds = null;
      
      for (const item of transcriptItems) {
        // Determine seconds (prefer numeric attribute)
        let seconds = null;
        
        // a) Direct attribute on the item
        const rawAttr = item.getAttribute('data-segment-start-time');
        if (rawAttr && !isNaN(rawAttr)) {
          seconds = Math.floor(parseFloat(rawAttr));
        }
        
        // b) Numeric attribute on a descendant
        if (seconds == null) {
          const tsNodeWithAttr = item.querySelector('[data-segment-start-time]');
          const attrVal = tsNodeWithAttr ? tsNodeWithAttr.getAttribute('data-segment-start-time') : null;
          if (attrVal && !isNaN(attrVal)) {
            seconds = Math.floor(parseFloat(attrVal));
          }
        }
        
        // c) Parse displayed timestamp text
        if (seconds == null) {
          let displayTs = '';
          const tsNode = item.querySelector('.ytd-transcript-segment-timestamp');
          if (tsNode && tsNode.textContent) {
            displayTs = tsNode.textContent.trim();
          } else {
            const textContent = item.textContent || '';
            const m3 = textContent.match(/\b(\d{1,2}:\d{2}:\d{2})\b/);
            const m2 = textContent.match(/\b(\d{1,2}:\d{2})\b/);
            if (m3) {
              displayTs = m3[1];
            } else if (m2) {
              displayTs = m2[1];
            }
          }
          
          if (displayTs) {
            const parts = displayTs.split(':');
            if (parts.length === 3) {
              // HH:MM:SS
              seconds = parseTime(displayTs);
            } else if (parts.length === 2) {
              // Ambiguous: try both and pick the one closer to previous segment
              const asMMSS = parseTime(displayTs);           // minutes:seconds
              const asHHMM = parseTranscriptTime(displayTs); // hours:minutes
              
              if (lastSeconds != null) {
                const dMMSS = Math.abs(asMMSS - lastSeconds);
                const dHHMM = Math.abs(asHHMM - lastSeconds);
                // Pick the candidate with smaller delta; ties prefer MM:SS
                seconds = dMMSS <= dHHMM ? asMMSS : asHHMM;
              } else {
                // No history yet: prefer MM:SS (YouTube shows MM:SS before 1h)
                seconds = asMMSS;
                // If clearly a >1h context and MM:SS would be unrealistically small vs duration, flip to HH:MM
                if (isFinite(videoDuration) && videoDuration >= 3600 && asHHMM <= videoDuration && asMMSS < 120) {
                  // Only flip if the HH:MM candidate is plausible and MM:SS is too small to be first meaningful segment
                  seconds = asHHMM;
                }
              }
            }
          }
        }
        
        // If we still couldn't determine a timestamp, skip this segment
        if (seconds == null || !isFinite(seconds)) continue;
        
        // Extract clean text (strip timestamp)
        let contentText = '';
        const textElement = item.querySelector('.ytd-transcript-segment-text, .ytd-transcript-segment-content');
        if (textElement && textElement.textContent) {
          contentText = textElement.textContent;
        } else {
          contentText = item.textContent || '';
        }
        
        contentText = contentText
          .replace(/\b\d{1,2}:\d{2}:\d{2}\b/, '')
          .replace(/\b\d{1,2}:\d{2}\b/, '')
          .replace(/\s+/g, ' ')
          .trim();
        
        if (!contentText) continue;
        
        // Drop out-of-range seconds if we know duration
        if (isFinite(videoDuration) && seconds > videoDuration + 1) continue;
        
        segments.push({
          timestamp: formatHHMMSS(seconds),
          text: contentText,
          seconds: seconds
        });
        
        lastSeconds = seconds;
      }
      
      // Deduplicate by text, prefer non-zero seconds; if both non-zero, keep earliest
      const byText = new Map();
      for (const seg of segments) {
        const key = seg.text;
        const existing = byText.get(key);
        if (!existing) {
          byText.set(key, seg);
        } else {
          if (existing.seconds === 0 && seg.seconds > 0) {
            byText.set(key, seg);
          } else if (existing.seconds > 0 && seg.seconds > 0 && seg.seconds < existing.seconds) {
            byText.set(key, seg);
          }
        }
      }
      
      transcriptData = Array.from(byText.values());
      
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
    
    // Create canvas to capture video frame (downscale if very large)
    const maxWidth = 1280;
    const maxHeight = 720;
    let targetWidth = video.videoWidth;
    let targetHeight = video.videoHeight;

    const widthRatio = maxWidth / targetWidth;
    const heightRatio = maxHeight / targetHeight;
    const scale = Math.min(1, widthRatio, heightRatio);

    if (scale < 1) {
      targetWidth = Math.floor(targetWidth * scale);
      targetHeight = Math.floor(targetHeight * scale);
    }

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    
    // Draw current video frame to canvas
    ctx.drawImage(video, 0, 0, targetWidth, targetHeight);
    
    // Convert to compressed JPEG to reduce storage size
    const screenshot = canvas.toDataURL('image/jpeg', 0.8);
    
    // Get current timestamp
    // const timestamp = formatTime(video.currentTime);
    const timestamp = formatHHMMSS(video.currentTime);
    
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
      } else {
        const err = response && response.error ? `: ${response.error}` : '';
        showNotification(`Failed to save screenshot${err}`, 'error');
        console.error('Failed to save screenshot', response);
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
    // const timestamp = formatTime(currentTime);
    const timestamp = formatHHMMSS(currentTime);
    console.log('Current Bookmark formatted time:', timestamp);
    
    // Get transcript around current time (20 seconds before and 20 seconds after)
    let transcript = '';
    let relevantTranscripts = [];
    
    if (transcriptData && transcriptData.length > 0) {
      console.log('Filtering transcript data...');
      relevantTranscripts = transcriptData.filter(item => {
        // Use the seconds property if available, otherwise parse the transcript timestamp as HH:MM
        const itemTime = (item.seconds !== undefined && item.seconds !== null)
          ? item.seconds
          : parseTranscriptTime(item.timestamp);
        // console.log('Transcript Item time:', itemTime, 'currentTime:', currentTime);
        return itemTime >= currentTime - 20 && itemTime <= currentTime + 20;
      });
      
      if (relevantTranscripts.length > 0) {
        // Sort by time and format nicely
        relevantTranscripts.sort((a, b) => {
          const ta = (a.seconds !== undefined && a.seconds !== null) ? a.seconds : parseTranscriptTime(a.timestamp);
          const tb = (b.seconds !== undefined && b.seconds !== null) ? b.seconds : parseTranscriptTime(b.timestamp);
          return ta - tb;
        });
        
        transcript = relevantTranscripts.map(item => {
          // const time = item.timestamp || formatTime((item.seconds !== undefined && item.seconds !== null) ? item.seconds : parseTranscriptTime(item.timestamp));
          const time = item.timestamp || formatHHMMSS((item.seconds !== undefined && item.seconds !== null) ? item.seconds : parseTranscriptTime(item.timestamp));
          return `${time}: ${item.text}`;
        }).join('\n');
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

// // Helper function to format time in MM:SS format
// function formatTime(seconds) {
//   const mins = Math.floor(seconds / 60);
//   const secs = Math.floor(seconds % 60);
//   return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
// }

// Helper function to format time in HH:MM:SS
function formatHHMMSS(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds || 0));
  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  return `${hrs.toString().padStart(2,'0')}:${mins.toString().padStart(2,'0')}:${secs.toString().padStart(2,'0')}`;
}

// Existing parseTime kept for navigation (supports MM:SS and HH:MM:SS)
function parseTime(timeString) {
  const parts = timeString.split(':').map(Number);
  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  } else if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  return 0;
}

// Parse transcript display timestamps (HH:MM or HH:MM:SS) into seconds
function parseTranscriptTime(timeString) {
  if (!timeString) return 0;
  const parts = timeString.split(':').map(Number);
  if (parts.length === 2) {
    // Treat as HH:MM (YouTube transcript uses HH:MM after 1h)
    return parts[0] * 3600 + parts[1] * 60;
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
      
      const timeMatch = timeLine.match(/(\d{2}):(\d{2}):(\d{2}),(\d{3})/);
      if (timeMatch) {
        const hours = parseInt(timeMatch[1]);
        const minutes = parseInt(timeMatch[2]);
        const seconds = parseInt(timeMatch[3]);
        const totalSeconds = hours * 3600 + minutes * 60 + seconds;
        
        segments.push({
          timestamp: formatHHMMSS(totalSeconds),
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
    if (line === 'WEBVTT' || line === '' || line.includes('-->')) {
      continue;
    }
    const timeMatch = line.match(/(\d{2}):(\d{2}):(\d{2})\.(\d{3})/);
    if (timeMatch) {
      if (currentTime && currentText) {
        const totalSeconds = parseTime(currentTime);
        segments.push({
          timestamp: formatHHMMSS(totalSeconds),
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
  if (currentTime && currentText) {
    const totalSeconds = parseTime(currentTime);
    segments.push({
      timestamp: formatHHMMSS(totalSeconds),
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
      return data.map(item => {
        const secs = item.seconds || parseTranscriptTime(item.timestamp || item.time || '0:00');
        return {
          timestamp: formatHHMMSS(secs),
          text: item.text || item.content || '',
          seconds: secs
        };
      });
    } else if (data.segments || data.transcript) {
      const segments = data.segments || data.transcript;
      return segments.map(item => {
        const secs = item.seconds || parseTranscriptTime(item.timestamp || item.time || '0:00');
        return {
          timestamp: formatHHMMSS(secs),
          text: item.text || item.content || '',
          seconds: secs
        };
      });
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
    // [HH:MM] or (HH:MM) or HH:MM
    const timeMatch = line.match(/(?:\[|\()?(\d{1,2}):(\d{2})(?:\]|\))?\s*(.+)/);
    if (timeMatch) {
      const hours = parseInt(timeMatch[1], 10);
      const minutes = parseInt(timeMatch[2], 10);
      const text = timeMatch[3].trim();
      const totalSeconds = hours * 3600 + minutes * 60;
      
      segments.push({
        timestamp: formatHHMMSS(totalSeconds),
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
  console.log('Adding transcript buttons...');
  const actionButtons = document.getElementById('youtube-notes-actions');
  console.log('Action buttons container:', actionButtons);
  
  if (actionButtons) {
    console.log('Creating transcript buttons...');
    
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
    console.log('Added refresh button');
    
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
    console.log('Added detect button');
    
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
    console.log('Added upload button');
    
    console.log('All transcript buttons added successfully');
  } else {
    console.error('Action buttons container not found!');
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
