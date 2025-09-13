import os
import cv2
import numpy as np
import uuid
import time
import threading
from flask import Flask, render_template, request, Response, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import queue
from mangum import Mangum
from background_creator import background_extraction, background_extraction_frame

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["RESULT_FOLDER"] = "static/results"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["RESULT_FOLDER"], exist_ok=True)

rtsp_thread = None
rtsp_stop_event = threading.Event()
frame_queue = queue.Queue(maxsize=1)  # Keeps only latest frame


def rtsp_processing(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("[Error] Cannot open RTSP stream.")
        return

    count = 0
    print("[Info] RTSP processing started.")

    while not rtsp_stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print("[Error] RTSP frame read failed, stopping stream.")
            break

        processed_frame = background_extraction_frame(frame)
        count += 1
        if count % 10 == 0:
            print(f"Got frame {count} from rtsp stream")
        if count >= 1000:
            count = 0
            print(f"Processed 1000 frames!")

        # Keep only the latest frame in the queue
        if not frame_queue.empty():
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass

        frame_queue.put(processed_frame)

        time.sleep(0.03)  # ~30 FPS max

    cap.release()
    print("[Info] RTSP processing stopped cleanly.")


def generate_mjpeg():
    while True:
        try:
            frame = frame_queue.get(timeout=1)  # Wait for the next frame

            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue

            frame_bytes = jpeg.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

        except queue.Empty:
            # If no frame is available, send a black frame or wait
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            ret, jpeg = cv2.imencode('.jpg', black_frame)
            frame_bytes = jpeg.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')


@app.route("/", methods=["GET", "POST"])
def index():
    global rtsp_thread

    if request.method == "POST":
        input_type = request.form.get("input_type")

        if input_type == "image_dir":
            image_dir = request.form.get("image_dir")
            result = background_extraction(image_dir, "image_dir")
            result_filename = f"{uuid.uuid4().hex}.jpg"
            result_path = os.path.join(app.config["RESULT_FOLDER"], result_filename)
            cv2.imwrite(result_path, result)
            return redirect(url_for("show_result", filename=result_filename))

        elif input_type == "video_file":
            file = request.files["video_file"]
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)

                result = background_extraction(file_path, "video_file")
                result_filename = f"{uuid.uuid4().hex}.jpg"
                result_path = os.path.join(app.config["RESULT_FOLDER"], result_filename)
                cv2.imwrite(result_path, result)
                return redirect(url_for("show_result", filename=result_filename))

        elif input_type == "rtsp":
            rtsp_url = request.form.get("rtsp_url")

            # Clear stop event before starting new thread
            rtsp_stop_event.clear()

            if rtsp_thread is None or not rtsp_thread.is_alive():
                rtsp_thread = threading.Thread(target=rtsp_processing, args=(rtsp_url,), daemon=True)
                rtsp_thread.start()

            return redirect(url_for("stream"))

        else:
            return "Invalid input type", 400

    return render_template("index.html")


@app.route("/result/<filename>")
def show_result(filename):
    return render_template("result.html", filename=filename)


@app.route("/stream")
def stream():
    return render_template("stream.html")


@app.route("/stop_stream", methods=["POST", "GET"])
def stop_stream():
    global rtsp_stop_event, rtsp_thread

    print("[Info] Received stop_stream request.")
    rtsp_stop_event.set()
    rtsp_thread = None  # Clear thread reference
    return "Stream stopped", 200


@app.route("/video_feed")
def video_feed():
    return Response(generate_mjpeg(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route("/static/results/<filename>")
def result_file(filename):
    return send_from_directory(app.config["RESULT_FOLDER"], filename)


# if __name__ == "__main__":
#     app.run(debug=True)

# Mangum to run on AWS Lambda. # Disable lifespan to avoid Flask 2.3+ TypeError
handler = Mangum(app, lifespan="off") # Important: This is the Lambda handler