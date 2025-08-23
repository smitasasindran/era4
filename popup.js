// Popup script for managing and displaying saved data
document.addEventListener('DOMContentLoaded', function() {
  // Tab switching functionality
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');
  
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      
      // Update active tab button
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      // Update active tab pane
      tabPanes.forEach(pane => pane.classList.remove('active'));
      document.getElementById(targetTab).classList.add('active');
      
      // Load data for the selected tab
      if (targetTab === 'screenshots') {
        loadScreenshots();
      } else {
        loadBookmarks();
      }
    });
  });
  
  // Load initial data
  loadScreenshots();
  
  // Event listeners for buttons
  document.getElementById('clearAllBtn').addEventListener('click', clearAllData);
  document.getElementById('exportBtn').addEventListener('click', exportData);
});

// Load and display screenshots
function loadScreenshots() {
  chrome.storage.local.get(['screenshots'], (result) => {
    const screenshots = result.screenshots || [];
    const container = document.getElementById('screenshotsContainer');
    
    if (screenshots.length === 0) {
      container.innerHTML = '<div class="empty-state">No screenshots yet</div>';
      return;
    }
    
    container.innerHTML = '';
    screenshots.reverse().forEach(screenshot => {
      const item = createScreenshotItem(screenshot);
      container.appendChild(item);
    });
  });
}

// Load and display bookmarks
function loadBookmarks() {
  chrome.storage.local.get(['bookmarks'], (result) => {
    const bookmarks = result.bookmarks || [];
    const container = document.getElementById('bookmarksContainer');
    
    if (bookmarks.length === 0) {
      container.innerHTML = '<div class="empty-state">No bookmarks yet</div>';
      return;
    }
    
    container.innerHTML = '';
    bookmarks.reverse().forEach(bookmark => {
      const item = createBookmarkItem(bookmark);
      container.appendChild(item);
    });
  });
}

// Create screenshot item element
function createScreenshotItem(screenshot) {
  const item = document.createElement('div');
  item.className = 'item screenshot-item';
  
  const videoInfo = document.createElement('div');
  videoInfo.className = 'video-info';
  videoInfo.innerHTML = `
    <h4>${screenshot.videoTitle}</h4>
    <p class="timestamp">⏰ ${screenshot.timestamp}</p>
    <p class="date">📅 ${new Date(screenshot.date).toLocaleDateString()}</p>
  `;
  
  const actions = document.createElement('div');
  actions.className = 'item-actions';
  
  const viewBtn = document.createElement('button');
  viewBtn.textContent = '👁️ View';
  viewBtn.className = 'action-btn view-btn';
  viewBtn.onclick = () => viewScreenshot(screenshot);
  
  const deleteBtn = document.createElement('button');
  deleteBtn.textContent = '🗑️ Delete';
  deleteBtn.className = 'action-btn delete-btn';
  deleteBtn.onclick = () => deleteScreenshot(screenshot.id);
  
  actions.appendChild(viewBtn);
  actions.appendChild(deleteBtn);
  
  item.appendChild(videoInfo);
  item.appendChild(actions);
  
  return item;
}

// Create bookmark item element
function createBookmarkItem(bookmark) {
  const item = document.createElement('div');
  item.className = 'item bookmark-item';
  
  const videoInfo = document.createElement('div');
  videoInfo.className = 'video-info';
  videoInfo.innerHTML = `
    <h4>${bookmark.videoTitle}</h4>
    <p class="timestamp">⏰ ${bookmark.timestamp}</p>
    <p class="date">📅 ${new Date(bookmark.date).toLocaleDateString()}</p>
  `;
  
  const transcript = document.createElement('div');
  transcript.className = 'transcript-preview';
  transcript.textContent = bookmark.transcript.length > 100 
    ? bookmark.transcript.substring(0, 100) + '...' 
    : bookmark.transcript;
  
  const actions = document.createElement('div');
  actions.className = 'item-actions';
  
  const viewBtn = document.createElement('button');
  viewBtn.textContent = '👁️ View';
  viewBtn.className = 'action-btn view-btn';
  viewBtn.onclick = () => viewBookmark(bookmark);
  
  const deleteBtn = document.createElement('button');
  deleteBtn.textContent = '🗑️ Delete';
  deleteBtn.className = 'action-btn delete-btn';
  deleteBtn.onclick = () => deleteBookmark(bookmark.id);
  
  actions.appendChild(viewBtn);
  actions.appendChild(deleteBtn);
  
  item.appendChild(videoInfo);
  item.appendChild(transcript);
  item.appendChild(actions);
  
  return item;
}

// View screenshot in new tab
function viewScreenshot(screenshot) {
  const newTab = window.open('', '_blank');
  newTab.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Screenshot - ${screenshot.videoTitle}</title>
      <style>
        body { margin: 0; padding: 20px; background: #f5f5f5; font-family: Arial, sans-serif; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 20px; }
        .info { margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .screenshot { text-align: center; }
        img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px; }
        .timestamp { font-weight: bold; color: #007bff; }
        .date { color: #6c757d; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>📸 Screenshot</h1>
        <div class="info">
          <p><strong>Video:</strong> ${screenshot.videoTitle}</p>
          <p class="timestamp">Timestamp: ${screenshot.timestamp}</p>
          <p class="date">Date: ${new Date(screenshot.date).toLocaleString()}</p>
        </div>
        <div class="screenshot">
          <img src="${screenshot.screenshot}" alt="Video Screenshot">
        </div>
      </div>
    </body>
    </html>
  `);
}

// View bookmark details
function viewBookmark(bookmark) {
  const newTab = window.open('', '_blank');
  newTab.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Bookmark - ${bookmark.videoTitle}</title>
      <style>
        body { margin: 0; padding: 20px; background: #f5f5f5; font-family: Arial, sans-serif; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 20px; }
        .info { margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .transcript { background: #f8f9fa; padding: 20px; border-radius: 5px; border-left: 4px solid #007bff; }
        .timestamp { font-weight: bold; color: #007bff; }
        .date { color: #6c757d; }
        pre { white-space: pre-wrap; font-family: inherit; margin: 0; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>🔖 Bookmark</h1>
        <div class="info">
          <p><strong>Video:</strong> ${bookmark.videoTitle}</p>
          <p class="timestamp">Timestamp: ${bookmark.timestamp}</p>
          <p class="date">Date: ${new Date(bookmark.date).toLocaleString()}</p>
        </div>
        <div class="transcript">
          <h3>Transcript (10s before and after):</h3>
          <pre>${bookmark.transcript}</pre>
        </div>
      </div>
    </body>
    </html>
  `);
}

// Delete screenshot
function deleteScreenshot(id) {
  if (confirm('Are you sure you want to delete this screenshot?')) {
    chrome.storage.local.get(['screenshots'], (result) => {
      const screenshots = result.screenshots || [];
      const updatedScreenshots = screenshots.filter(s => s.id !== id);
      chrome.storage.local.set({ screenshots: updatedScreenshots }, () => {
        loadScreenshots();
      });
    });
  }
}

// Delete bookmark
function deleteBookmark(id) {
  if (confirm('Are you sure you want to delete this bookmark?')) {
    chrome.storage.local.get(['bookmarks'], (result) => {
      const bookmarks = result.bookmarks || [];
      const updatedBookmarks = bookmarks.filter(b => b.id !== id);
      chrome.storage.local.set({ bookmarks: updatedBookmarks }, () => {
        loadBookmarks();
      });
    });
  }
}

// Clear all data
function clearAllData() {
  if (confirm('Are you sure you want to clear all data? This action cannot be undone.')) {
    chrome.storage.local.clear(() => {
      loadScreenshots();
      loadBookmarks();
    });
  }
}

// Export data
function exportData() {
  chrome.storage.local.get(['screenshots', 'bookmarks'], (result) => {
    const data = {
      exportDate: new Date().toISOString(),
      screenshots: result.screenshots || [],
      bookmarks: result.bookmarks || []
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `youtube-notes-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
  });
}
