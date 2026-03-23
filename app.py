import os
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify, url_for
from werkzeug.utils import secure_filename

from cartoonify import cartoonify_image, load_image_bgr, save_image_bgr

# -----------------------------
# Flask setup
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
RESULT_DIR = STATIC_DIR / "results"
TEMPLATES_DIR = BASE_DIR / "templates"

for p in (UPLOAD_DIR, RESULT_DIR):
    p.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR),
)


# -----------------------------
# Helpers
# -----------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def new_name(suffix: str = ".png") -> str:
    return f"{uuid.uuid4().hex}{suffix}"


# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """
    Expects form fields:
      file: image
      blur_type: 'bilateral' | 'median' | 'gaussian'
      quantizer: 'kmeans' | 'mediancut'
      num_colors: int [4..16]
      line_strength: float [0.1..1.0]
      target_long_side: int px
      upscale_small: 'true' | 'false'
    """
    if "file" not in request.files:
        return jsonify({"error": "No file field"}), 400

    f = request.files["file"]
    if not f or f.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "Unsupported format"}), 400

    # Save upload
    ext = "." + f.filename.rsplit(".", 1)[1].lower()
    safe = secure_filename(f.filename)
    if not allowed_file(safe):
        safe = new_name(ext)
    upload_name = new_name(ext)
    upload_path = UPLOAD_DIR / upload_name
    f.save(str(upload_path))

    # Read params with sane fallbacks
    blur_type = request.form.get("blur_type", "bilateral").lower()
    quantizer = request.form.get("quantizer", "kmeans").lower()
    try:
        num_colors = int(request.form.get("num_colors", 8))
    except Exception:
        num_colors = 8
    try:
        line_strength = float(request.form.get("line_strength", 0.5))
    except Exception:
        line_strength = 0.5
    try:
        target_long_side = int(request.form.get("target_long_side", 1024))
    except Exception:
        target_long_side = 1024
    upscale_small = request.form.get("upscale_small", "true").lower() == "true"

    # Process
    try:
        src = load_image_bgr(str(upload_path))
        out = cartoonify_image(
            src,
            blur_type=blur_type,
            quantizer=quantizer,
            num_colors=max(4, min(32, num_colors)),
            line_strength=max(0.05, min(2.0, line_strength)),
            target_long_side=max(256, min(4096, target_long_side)),
            upscale_small=upscale_small,
        )
    except Exception as e:
        return jsonify({"error": f"Processing failed: {e}"}), 500

    # Save result as PNG to avoid JPG re-compress artifacts
    result_name = new_name(".png")
    result_path = RESULT_DIR / result_name
    save_image_bgr(out, str(result_path))

    return jsonify(
        {
            "ok": True,
            "cartoon_image_url": url_for("static", filename=f"results/{result_name}"),
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = bool(int(os.environ.get("DEBUG", "0")))
    app.run(host="0.0.0.0", port=port, debug=debug)
