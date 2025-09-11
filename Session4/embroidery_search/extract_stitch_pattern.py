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
OUTPUT_GRID_IMAGE = 'detected_grid_lines.png'
OUTPUT_MATRIX_CSV = 'pattern_matrix.csv'
OUTPUT_MAPPING_JSON = 'symbol_to_number_mapping.json'
DPI = 300

# Specify tesseract executable path if needed
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# -------- Step 1: Convert PDF to Image --------
print("[INFO] Converting PDF to image...")
images = convert_from_path(PDF_FILE, dpi=DPI)
images[0].save(OUTPUT_IMAGE, 'PNG')

# -------- Step 2: Preprocess Image --------
print("[INFO] Preprocessing image...")
img = cv2.imread(OUTPUT_IMAGE)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray, (3, 3), 0)

binary = cv2.adaptiveThreshold(blur, 255,
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 15, 5)

kernel = np.ones((2, 2), np.uint8)
binary = cv2.dilate(binary, kernel, iterations=1)

# -------- Step 3: Detect Grid Lines with Hough Transform --------
print("[INFO] Detecting grid lines...")
lines = cv2.HoughLinesP(binary, rho=1, theta=np.pi/180, threshold=200,
                        minLineLength=50, maxLineGap=10)

horizontal_lines_img = np.zeros_like(binary)
vertical_lines_img = np.zeros_like(binary)

for line in lines:
    x1, y1, x2, y2 = line[0]
    angle = np.arctan2(y2 - y1, x2 - x1) * (180 / np.pi)

    if abs(angle) < 10 or abs(angle - 180) < 10:
        cv2.line(horizontal_lines_img, (x1, y1), (x2, y2), 255, 1)
    elif abs(angle - 90) < 10 or abs(angle + 90) < 10:
        cv2.line(vertical_lines_img, (x1, y1), (x2, y2), 255, 1)

grid_lines = cv2.add(horizontal_lines_img, vertical_lines_img)
cv2.imwrite(OUTPUT_GRID_IMAGE, grid_lines)

# -------- Step 4: Find Grid Cell Intersections --------
print("[INFO] Detecting grid cell intersections...")
# Find intersection points
intersections = cv2.bitwise_and(horizontal_lines_img, vertical_lines_img)

# Detect corner points using goodFeaturesToTrack
corners = cv2.goodFeaturesToTrack(intersections, maxCorners=1000, qualityLevel=0.01, minDistance=10)
corners = np.int0(corners)

# Sort corners top-to-bottom, left-to-right
corners = sorted(corners, key=lambda c: (c.ravel()[1], c.ravel()[0]))

# Heuristic: Determine grid size by counting unique Y and X coordinates
ys = sorted(list(set(c.ravel()[1] for c in corners)))
xs = sorted(list(set(c.ravel()[0] for c in corners)))
num_rows = len(ys) - 1
num_cols = len(xs) - 1

# -------- Step 5: Extract Cells and Recognize Symbols --------
print("[INFO] Extracting cells and recognizing symbols...")
symbol_to_number = {'.': 0}
matrix = np.zeros((num_rows, num_cols), dtype=int)

for row in range(num_rows):
    for col in range(num_cols):
        x1 = xs[col]
        y1 = ys[row]
        x2 = xs[col + 1]
        y2 = ys[row + 1]

        cell_img = binary[y1:y2, x1:x2]

        symbol = pytesseract.image_to_string(cell_img, config='--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789').strip()

        if len(symbol) == 0:
            symbol = '.'

        if symbol not in symbol_to_number:
            symbol_to_number[symbol] = len(symbol_to_number)

        matrix[row, col] = symbol_to_number[symbol]

# -------- Step 6: Export Matrix and Mapping --------
print("[INFO] Saving results...")
df = pd.DataFrame(matrix)
df.to_csv(OUTPUT_MATRIX_CSV, index=False)

with open(OUTPUT_MAPPING_JSON, 'w') as f:
    json.dump(symbol_to_number, f, indent=4)

print(f"[SUCCESS] Matrix saved to {OUTPUT_MATRIX_CSV}")
print(f"[SUCCESS] Symbol mapping saved to {OUTPUT_MAPPING_JSON}")
print(f"[INFO] Grid visualization saved to {OUTPUT_GRID_IMAGE}")
