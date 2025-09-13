import streamlit as st
import cv2
import numpy as np
import os
from glob import glob
import time
from background_creator import estimate_background_batch, convert_to_bytes, sample_video_frames, get_foreground_mask


def initialize_background_from_stream(cap, init_frames=30, method="median", threshold=30):
    """Estimate background using median of first N frames from a video stream."""
    frames = []
    st.info(f"Capturing {init_frames} frames to initialize background...")
    for i in range(init_frames):
        ret, frame = cap.read()
        if not ret:
            st.warning(f"Stopped early: only {i} frames captured.")
            break
        frames.append(frame)
    st.success(f"Background initialized with {len(frames)} frames.")
    # return initialize_background_from_batch(frames)
    return estimate_background_batch(frames, method=method, threshold=threshold).astype(np.float32)


# -------------------------------
# Streamlit UI
# -------------------------------
# st.set_page_config(layout="wide")
st.title("Background Estimation")
st.markdown(f"**(Extract background from image batch, video or RTSP Stream)**")

st.markdown("#### Choose Input Mode")

# Custom CSS for bigger radio-like buttons, to globally reduce container widths
st.markdown(
    """
    <style>
    div[data-baseweb="radio"] > div {
        flex-direction: row !important;
        justify-content: center;
    }
    div[data-baseweb="radio"] label {
        font-size: 18px !important;
        font-weight: 600 !important;
        margin-right: 2rem;
    }
    .stSelectbox, .stRadio, .stSlider, .stExpander, .stTextInput, .stFileUploader {
        max-width: 600px;     /* set desired width */
        //margin: auto;       /* center align, uncomment if needed */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# # Use custom CSS to globally reduce container widths
# st.markdown("""
#     <style>
#     .stSelectbox, .stRadio, .stSlider, .stExpander, .stTextInput, .stFileUploader {
#         max-width: 600px;   /* set desired width */
#         //margin: auto;       /* center align, uncomment if needed */
#     }
#     </style>
# """, unsafe_allow_html=True)


# Track selected mode to reset state when user switches
if "last_mode" not in st.session_state:
    st.session_state.last_mode = None
if "final_bg" not in st.session_state:
    st.session_state.final_bg = None

mode = st.radio(
    "Choose Input Mode",
    ["Image Directory", "Video File", "RTSP Stream"],
    horizontal=True,  # works in new Streamlit
    label_visibility="collapsed"
)

# --- Reset background result when mode changes ---
if st.session_state.last_mode != mode:
    st.session_state.final_bg = None
    st.session_state.last_mode = mode

# --- Parameters ---
st.markdown("##### Parameters:")

method = st.selectbox(
    "Background Estimation Method:",
    ["median", "mode", "mog2"],
    help=(
        "Choose how the background is estimated:\n\n"
        "• **Median** – Robust to moving objects, good general choice.\n"
        "• **Mode** – Picks the most frequent pixel value, useful if background repeats consistently.\n"
        "• **MOG2** – OpenCV's adaptive background subtractor, handles gradual lighting changes."
    )
)

with st.expander("⚙️ Advanced Options"):
    refine_iters = st.slider(
        "Refinement Iterations",
        1, 100, 20,
        help=(
            "Number of times the background is refined using accumulateWeighted.\n\n"
            "• Higher = smoother, cleaner background but slower.\n"
            "• Lower = faster but may keep noise/moving objects."
        )
    )

    alpha = st.slider(
        "Learning Rate (alpha)",
        0.001, 0.1, 0.01, step=0.001,
        help=(
            "Controls how quickly the background adapts to new frames.\n\n"
            "• Small values (e.g. 0.001) → very stable, ignores short-term motion.\n"
            "• Large values (e.g. 0.1) → adapts faster, but may absorb moving objects."
        )
    )

    threshold = st.slider(
        "Foreground Threshold (For Video and RTSP)",
        10, 100, 30, step=5,
        help=(
            "Pixel intensity difference required to classify a pixel as foreground.\n\n"
            "• Low values → more sensitive, may detect noise.\n"
            "• High values → less sensitive, may miss subtle movements."
        )
    )

# -------------------------------
# Mode-specific logic
# -------------------------------


if mode == "Image Directory":
    # mcol1, mcol2 = st.columns([0.7, 1])
    # with mcol1:
    directory = st.text_input("Enter directory path containing images:")

    if directory and os.path.isdir(directory):
        print(f"Looking for images in {directory}...")  # st.info()
        image_paths = sorted(glob(os.path.join(directory, "*.jpg")) + glob(os.path.join(directory, "*.png")))

        if image_paths:
            images = [cv2.imread(p) for p in image_paths]
            st.success(f"Loaded {len(images)} images from {directory}")

            # Compute background if not already done or sliders changed
            print(f"Estimating background using method: {method.upper()}...")
            # final_bg = estimate_background_batch(images, method=method, threshold=threshold)
            st.session_state.final_bg = estimate_background_batch(
                images, method=method, threshold=threshold, alpha=alpha, refine_iters=refine_iters
            )

            print("Final background estimation complete.")

            # # Show only final background
            # st.image(cv2.cvtColor(final_bg, cv2.COLOR_BGR2RGB), caption="Final Estimated Background")

            # # Download button
            # st.download_button(
            #     label="Download Background Image",
            #     data=convert_to_bytes(final_bg),
            #     file_name="background.jpg",
            #     mime="image/jpeg",
            #     key="download_button_image"
            # )

        else:
            st.warning("No images found in the directory.")

    # Display result if available
    if st.session_state.final_bg is not None:
        # Show only final background
        st.image(cv2.cvtColor(st.session_state.final_bg, cv2.COLOR_BGR2RGB), caption="Final Estimated Background")

        # Download button
        st.download_button(
            label="Download Background Image",
            data=convert_to_bytes(st.session_state.final_bg),
            file_name="background.jpg",
            mime="image/jpeg",
            key="download_button_image"
        )


elif mode == "Video File":
    video_file = st.file_uploader("Upload a video file", type=["mp4", "avi", "mov"])
    # sampling_fps = st.slider(
    #     "Sampling FPS (frames per second)",
    #     1, 10, 1, step=1,
    #     help="Controls how frequently frames are sampled from the video. "
    #          "Higher FPS = more frames → potentially better background, "
    #          "but slower processing."
    # )
    sampling_fps = 1  # fixed for now

    if video_file:
        with open("temp_video.mp4", "wb") as f:
            f.write(video_file.read())

        st.info(f"Extracting frames at {sampling_fps} FPS for batch background estimation...")
        frames = sample_video_frames("temp_video.mp4", fps=sampling_fps)

        if frames:
            st.success(f"Extracted {len(frames)} frames from video")
            # final_bg = estimate_background_batch(
            #     frames, method=method, threshold=threshold, alpha=alpha, refine_iters=refine_iters
            # )
            st.session_state.final_bg = estimate_background_batch(
                frames, method=method, threshold=threshold, alpha=alpha, refine_iters=refine_iters
            )

            # st.image(cv2.cvtColor(final_bg, cv2.COLOR_BGR2RGB), caption="Final Estimated Background")

            # st.download_button(
            #     label="Download Background Image",
            #     data=convert_to_bytes(final_bg),
            #     file_name="background_from_video.jpg",
            #     mime="image/jpeg",
            #     key="download_button_video"
            # )
        else:
            st.warning("No frames extracted from video.")

    # Display result if available
    if st.session_state.final_bg is not None:
        st.image(cv2.cvtColor(st.session_state.final_bg, cv2.COLOR_BGR2RGB), caption="Final Estimated Background")
        st.download_button(
            label="Download Background Image",
            data=convert_to_bytes(st.session_state.final_bg),
            file_name="background_from_video.jpg",
            mime="image/jpeg",
            key="download_button_video"
        )


elif mode == "RTSP Stream":
    rtsp_url = st.text_input("Enter RTSP Stream URL:")

    if rtsp_url:
        cap = cv2.VideoCapture(rtsp_url)
        if cap.isOpened():
            st.info("Initializing background from stream...")
            background = initialize_background_from_stream(
                cap, init_frames=30, method=method, threshold=threshold
            ).astype("float")

            stframe1 = st.empty()
            stframe2 = st.empty()
            stframe3 = st.empty()
            fps_display = st.empty()
            download_bg_btn = st.empty()

            st.success("Streaming started. Processing frames...")

            frame_count = 0
            prev_time = time.time()

            while True:
                ret, frame = cap.read()
                if not ret:
                    st.error("Stream ended or cannot fetch frames.")
                    break

                frame_count += 1
                start_time = time.time()

                # Update background
                cv2.accumulateWeighted(frame, background, alpha)
                bg = cv2.convertScaleAbs(background)
                mask = get_foreground_mask(frame, bg, threshold)

                # Display results in Streamlit
                stframe1.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), caption=f"Original Frame #{frame_count}")
                stframe2.image(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB), caption="Estimated Background")
                stframe3.image(mask, caption="Foreground Mask (Refined)", channels="GRAY")

                # FPS calculation
                end_time = time.time()
                fps = 1 / (end_time - start_time)
                fps_display.metric("⚡ FPS (Frames per Second)", f"{fps:.2f}")

                # Update logs every 20 frames
                if frame_count % 20 == 0:
                    st.write(f"Processed {frame_count} frames...")

                # Update download button dynamically
                download_bg_btn.download_button(
                    label="Download Current Background",
                    data=convert_to_bytes(bg),
                    file_name="background_stream.jpg",
                    mime="image/jpeg",
                    key=f"download_button_rtsp_{frame_count}"
                )

        else:
            st.error("Unable to open RTSP stream. Please check the URL.")