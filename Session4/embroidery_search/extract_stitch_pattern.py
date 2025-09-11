import cv2
import numpy as np
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
import json
import os

# -------- Configuration --------
PDF_FILE = 'Anchor-Modern-Landscape-pattern.pdf'
OUTPUT_IMAGE = 'pattern_page.png'
OUTPUT_MATRIX_CSV = 'pattern_matrix.csv'
OUTPUT_MAPPING_JSON = 'symbol_to_number_mapping.json'
DPI = 300

# -------- Step 1: Convert PDF to Image --------
print("[INFO] Converting PDF to image...")
images = convert_from_path(PDF_FILE, dpi=DPI)
images[0].save(OUTPUT_IMAGE, 'PNG')

# -------- Step 2: Preprocess Image --------
print("[INFO] Preprocessing image...")
img = cv2.imread(OUTPUT_IMAGE)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
binary = cv2.adaptiveThreshold(gray, 255,
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 11, 2)

kernel = np.ones((3,3), np.uint8)
binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

# -------- Step 3: Detect Grid Lines --------
print("[INFO] Detecting grid lines...")
horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40,1))
vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,40))

horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

grid_lines = cv2.add(horizontal_lines, vertical_lines)

# -------- Step 4: Find Grid Cells --------
print("[INFO] Finding grid cells...")
contours, _ = cv2.findContours(grid_lines, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
bounding_boxes = [cv2.boundingRect(c) for c in contours]

# Filter out very small boxes (noise)
bounding_boxes = [b for b in bounding_boxes if b[2] > 10 and b[3] > 10]

# Sort top-to-bottom, left-to-right
bounding_boxes = sorted(bounding_boxes, key=lambda b: (b[1], b[0]))

num_cells = len(bounding_boxes)
num_cols = int(np.sqrt(num_cells))
num_rows = num_cols  # Assumption: roughly square grid

# -------- Step 5: Extract Cells and Recognize Symbols --------
print("[INFO] Extracting cells and recognizing symbols...")
symbol_to_number = {'.': 0}  # Empty cell mapping
matrix = np.zeros((num_rows, num_cols), dtype=int)

for idx, (x, y, w, h) in enumerate(bounding_boxes):
    cell_img = binary[y:y+h, x:x+w]

    symbol = pytesseract.image_to_string(cell_img, config='--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789').strip()
    # OCR single symbol per cell
    # symbol = pytesseract.image_to_string(cell_img, config='--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789').strip()

    if len(symbol) == 0:
        symbol = '.'

    if symbol not in symbol_to_number:
        symbol_to_number[symbol] = len(symbol_to_number)

    row = idx // num_cols
    col = idx % num_cols
    if row < num_rows and col < num_cols:
        matrix[row, col] = symbol_to_number[symbol]

# -------- Step 6: Export Matrix and Mapping --------
print("[INFO] Saving results...")
df = pd.DataFrame(matrix)
df.to_csv(OUTPUT_MATRIX_CSV, index=False)

with open(OUTPUT_MAPPING_JSON, 'w') as f:
    json.dump(symbol_to_number, f, indent=4)

print(f"[SUCCESS] Matrix saved to {OUTPUT_MATRIX_CSV}")
print(f"[SUCCESS] Symbol mapping saved to {OUTPUT_MAPPING_JSON}")
