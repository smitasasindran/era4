import cv2
import numpy as np
import os
from glob import glob

# -------------------------------
# Helper Functions
# -------------------------------

def background_extraction(input_path, input_type):
    """
    Static background extraction for image_dir or video_file mode.
    Returns final result image (OpenCV image).
    """
    if input_type == "image_dir":
        images = load_images_from_directory(input_path)
    elif input_type == "video_file":
        images = sample_video_frames(input_path, fps=1)
    else:
        raise ValueError("Unsupported static input_type")

    if not images:
        raise ValueError("No images found for processing")

    background = estimate_background_batch(images, method="median", alpha=0.01)

    # Use the last frame for foreground mask extraction
    last_frame = images[-1]
    mask = get_foreground_mask(last_frame, background)

    # Apply mask to get foreground
    result = cv2.bitwise_and(last_frame, last_frame, mask=mask)
    return background  # Return final result (as OpenCV image)


def background_extraction_frame(frame):
    """
    Real-time per-frame background extraction for RTSP mode.
    Returns the processed frame.
    """
    # Simple running average background estimation (could be improved)
    if not hasattr(background_extraction_frame, "bg_float"):
        background_extraction_frame.bg_float = frame.astype(np.float32)

    # Update background model with running average
    alpha = 0.01
    cv2.accumulateWeighted(frame, background_extraction_frame.bg_float, alpha)
    background = cv2.convertScaleAbs(background_extraction_frame.bg_float)

    mask = get_foreground_mask(frame, background)

    # Apply mask to get foreground
    result = cv2.bitwise_and(frame, frame, mask=mask)
    return background


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

