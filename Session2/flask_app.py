import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename

# Assume you already have this function implemented:
# def background_extraction(input_path, input_type): -> returns result_image_path
# from your_background_module import background_extraction
from background_creator


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["RESULT_FOLDER"] = "static/results"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["RESULT_FOLDER"], exist_ok=True)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        input_type = request.form.get("input_type")

        # Generate unique filename for results
        result_filename = f"{uuid.uuid4().hex}.jpg"
        result_path = os.path.join(app.config["RESULT_FOLDER"], result_filename)

        if input_type == "image_dir":
            # Expecting directory path from user
            image_dir = request.form.get("image_dir")
            result = background_extraction(image_dir, "image_dir")

        elif input_type == "video_file":
            file = request.files["video_file"]
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)
                result = background_extraction(file_path, "video_file")

        elif input_type == "rtsp":
            rtsp_url = request.form.get("rtsp_url")
            result = background_extraction(rtsp_url, "rtsp")

        else:
            return "Invalid input type", 400

        # Save result image into static folder
        result.save(result_path)  # Assuming your function returns a PIL Image or OpenCV image
        return redirect(url_for("show_result", filename=result_filename))

    return render_template("index.html")


@app.route("/result/<filename>")
def show_result(filename):
    return render_template("result.html", filename=filename)


@app.route("/static/results/<filename>")
def result_file(filename):
    return send_from_directory(app.config["RESULT_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True)
