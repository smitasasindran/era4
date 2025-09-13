import cv2
import numpy as np
import os
from glob import glob

# -------------------------------
# Helper Functions
# -------------------------------

def estimate_background_batch(images, method="median", threshold=30, alpha=0.01, refine_iters=20):
    """
    Estimate background from a batch of images with initialization + refinement.
    """
    if not images:
        raise ValueError("No images provided")

    # Step 1: Initialize background
    H, W, C = images[0].shape
    if method == "median":
        background = np.median(np.stack(images, axis=3), axis=3).astype(np.uint8)
    elif method == "mode":
        stack = np.stack(images, axis=3)
        background = np.zeros((H, W, C), dtype=np.uint8)
        for c in range(C):
            def pixel_mode(x):
                return np.bincount(x, minlength=256).argmax()
            background[:, :, c] = np.apply_along_axis(pixel_mode, axis=2, arr=stack[:, :, c, :]).astype(np.uint8)
    elif method == "mog2":
        fgbg = cv2.createBackgroundSubtractorMOG2(history=len(images), varThreshold=50, detectShadows=False)
        for img in images:
            fgbg.apply(img)
        background = fgbg.getBackgroundImage()
    else:
        raise ValueError("Invalid method. Choose 'median', 'mode', or 'mog2'")

    # Step 2: Refine with accumulateWeighted
    bg_float = background.astype(np.float32)
    for i in range(min(refine_iters, len(images))):
        cv2.accumulateWeighted(images[i], bg_float, alpha)
    background = cv2.convertScaleAbs(bg_float)

    return background



# def initialize_background_from_batch(images):
#     """Estimate background using median of a batch of images."""

#     # Stack images along a new axis
#     stack = np.stack(images, axis=3)  # shape: (H, W, C, N)

#     # Compute median along the time axis (axis=3)
#     background = np.median(stack, axis=3).astype(np.uint8)

#     # return np.median(np.stack(images, axis=3), axis=3).astype(np.uint8)

#     #fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=True)

#     return background




def refine_mask(mask, kernel_size=5, iterations=2):
    """Apply morphological operations to clean noise in the mask."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)  # remove noise
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=iterations) # fill gaps
    return mask


def get_foreground_mask(frame, background, threshold=30):
    """Compute foreground mask."""
    diff = cv2.absdiff(frame, background)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    return refine_mask(mask)


def convert_to_bytes(image):
    """Convert OpenCV image to bytes (for download button)."""
    _, buf = cv2.imencode(".jpg", image)
    return buf.tobytes()


def load_images_from_directory(directory):
    """Load all .jpg/.png images from a directory."""
    image_paths = sorted(glob(os.path.join(directory, "*.jpg")) + glob(os.path.join(directory, "*.png")))
    images = [cv2.imread(p) for p in image_paths if cv2.imread(p) is not None]
    return images


def sample_video_frames(video_path, fps=1):
    """Sample frames from video at given fps."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    native_fps = cap.get(cv2.CAP_PROP_FPS)
    if native_fps <= 0:
        native_fps = 30  # fallback

    interval = int(round(native_fps / fps))
    frames, frame_count = [], 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % interval == 0:
            frames.append(frame)
        frame_count += 1

    cap.release()
    return frames

