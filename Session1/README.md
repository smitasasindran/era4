# YouTube Notes & Screenshots Chrome Extension

A powerful Chrome extension that allows you to take notes on YouTube videos without needing to log in. Take screenshots at specific timestamps and bookmark moments with transcript context.

## Features

- **📸 Screenshots**: Capture video frames at specific timestamps
- **🔖 Bookmarks**: Save timestamps with transcript context (10 seconds before and after)
- **⌨️ Keyboard Shortcuts**: Quick access to features
- **💾 Local Storage**: All data stored locally in your browser
- **📱 Beautiful UI**: Modern, responsive interface
- **🚀 No Login Required**: Works completely offline

## Keyboard Shortcuts

- **Ctrl+Shift+S** (Windows/Linux) or **Cmd+Shift+S** (Mac): Take a screenshot
- **Ctrl+Shift+B** (Windows/Linux) or **Cmd+Shift+B** (Mac): Bookmark timestamp with transcript

## Installation

### Method 1: Load Unpacked Extension (Recommended for Development)

1. Download or clone this repository to your local machine
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" in the top right corner
4. Click "Load unpacked" and select the folder containing the extension files
5. The extension should now appear in your extensions list

### Method 2: Create Icons

Before installing, you'll need to create icon files:
- `icons/icon16.png` (16x16 pixels)
- `icons/icon48.png` (48x48 pixels)  
- `icons/icon128.png` (128x128 pixels)

You can use any image editor or download free icons from sites like:
- [Flaticon](https://www.flaticon.com/)
- [Icons8](https://icons8.com/)
- [Feather Icons](https://feathericons.com/)


If you want to use the 'Export PDF' option, you may need to download these pdf-related libraries to your local folder, before 'Load unpacked' to chrome extension. Create a local directory, example: 
mkdir libs
curl -L -o libs/jspdf.umd.min.js https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js
curl -L -o libs/jspdf.plugin.autotable.min.js https://cdn.jsdelivr.net/npm/jspdf-autotable@3.5.29/dist/jspdf.plugin.autotable.min.js


## Usage

### Taking Screenshots

1. Navigate to any YouTube video
2. Play the video and pause at the desired moment
3. Use the keyboard shortcut **Ctrl+Shift+S** or click the floating "📸 Screenshot" button
4. The screenshot will be saved with the current timestamp

### Bookmarking Timestamps

1. Navigate to any YouTube video
2. Play the video to the desired timestamp
3. Use the keyboard shortcut **Ctrl+Shift+B** or click the floating "🔖 Bookmark" button
4. The extension will capture the transcript 10 seconds before and after the current time

### Managing Your Notes

1. Click the extension icon in your Chrome toolbar
2. Use the tabs to switch between Screenshots and Bookmarks
3. View, delete, or export your saved data
4. Use the "Clear All" button to remove all data
5. Use the "Export" button to download your data as JSON

## File Structure

```
youtube-notes-extension/
├── manifest.json          # Extension configuration
├── background.js          # Background service worker
├── content.js            # Content script for YouTube pages
├── popup.html            # Extension popup interface
├── popup.js              # Popup functionality
├── styles.css            # Styling for popup and content
├── icons/                # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md             # This file
```

## How It Works

### Content Script (`content.js`)
- Runs on YouTube pages
- Detects video elements and extracts metadata
- Captures video frames for screenshots
- Retrieves transcript data
- Adds floating action buttons to the page

### Background Script (`background.js`)
- Handles keyboard shortcuts
- Manages communication between components
- Stores data in Chrome's local storage

### Popup Interface (`popup.html/popup.js`)
- Displays saved screenshots and bookmarks
- Provides management tools (view, delete, export)
- Shows keyboard shortcut information

## Data Storage

All data is stored locally in your browser using Chrome's `chrome.storage.local` API:

- **Screenshots**: Base64-encoded PNG images with metadata
- **Bookmarks**: Timestamp, video info, and transcript context
- **No data is sent to external servers**

## Troubleshooting

### Extension Not Working
1. Make sure you're on a YouTube video page
2. Check that the extension is enabled in `chrome://extensions/`
3. Try refreshing the page
4. Check the browser console for error messages

### Screenshots Not Working
1. Ensure the video is playing or paused (not loading)
2. Check that the video element is present on the page
3. Try refreshing the page and waiting for the video to load

### Transcripts Not Available
1. Not all YouTube videos have transcripts
2. The extension automatically tries to load available transcripts
3. If no transcript is available, it will show "No transcript available for this timestamp"

### Keyboard Shortcuts Not Working
1. Make sure you're on a YouTube page
2. Check that no other extensions are conflicting
3. Try the floating buttons as an alternative

## Privacy & Security

- **No data collection**: The extension doesn't collect or transmit any personal data
- **Local storage only**: All data is stored locally in your browser
- **No external requests**: The extension doesn't make any network requests
- **Open source**: Full transparency of what the extension does

## Browser Compatibility

- **Chrome**: Full support (tested)
- **Edge**: Should work (Chromium-based)
- **Opera**: Should work (Chromium-based)
- **Firefox**: Not supported (different extension API)

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the extension.

## License

This project is open source and available under the MIT License.

## Support

If you encounter any issues or have questions:
1. Check the troubleshooting section above
2. Look for similar issues in the project repository
3. Create a new issue with detailed information about your problem

---

**Note**: This extension is designed for personal use and educational purposes. Please respect YouTube's terms of service and copyright laws when using this tool.
