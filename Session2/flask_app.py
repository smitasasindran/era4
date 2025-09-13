import os
import cv2
import uuid
import threading
from flask import Flask, render_template, request, Response, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename

from background_creator import background_extraction, background_extraction_frame

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["RESULT_FOLDER"] = "static/results"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["RESULT_FOLDER"], exist_ok=True)

rtsp_frame = None
rtsp_lock = threading.Lock()
rtsp_thread = None


def rtsp_processing(rtsp_url):
    global rtsp_frame, rtsp_lock

    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("[Error] Cannot open RTSP stream.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        processed_frame = background_extraction_frame(frame)

        with rtsp_lock:
            rtsp_frame = processed_frame

    cap.release()


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


def generate_mjpeg():
    global rtsp_frame, rtsp_lock

    while True:
        with rtsp_lock:
            if rtsp_frame is None:
                continue

            ret, jpeg = cv2.imencode('.jpg', rtsp_frame)
            if not ret:
                continue

            frame = jpeg.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


@app.route("/video_feed")
def video_feed():
    return Response(generate_mjpeg(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route("/static/results/<filename>")
def result_file(filename):
    return send_from_directory(app.config["RESULT_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True)
