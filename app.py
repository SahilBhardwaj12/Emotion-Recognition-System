"""
EmoStudyAI — app.py
Complete Flask backend — works LOCAL and CLOUD (Render/Railway)
Model download handled by utils/predict.py on first prediction
"""
from dotenv import load_dotenv
import os

load_dotenv()
from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session
from flask_cors import CORS
import cv2
import threading
import time
import json
import os
import base64
import numpy as np
from datetime import datetime
import torch
torch.set_num_threads(1)

# ─────────────────────────────────────────────
# Utils
# ─────────────────────────────────────────────
from utils.predict        import predict_emotion
from utils.recommendation import get_recommendation
from utils.database       import init_db, save_emotion, get_history, get_emotion_counts
from utils.youtube_api    import get_study_videos
from utils.gemini_api     import get_ai_study_advice
from utils.quotes_api     import get_motivational_quote

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "emostudyai_secret_key_2026"
CORS(app)

USERS_FILE = "database/users.json"

# Detect cloud environment
IS_CLOUD = bool(
    os.environ.get("RAILWAY_ENVIRONMENT") or
    os.environ.get("RENDER") or
    os.environ.get("CLOUD")
)
print(f"RENDER env: {os.environ.get('RENDER')}")
print(f"IS_CLOUD: {IS_CLOUD}")
print(f"[EmoStudyAI] Running in {'CLOUD' if IS_CLOUD else 'LOCAL'} mode")

# ─────────────────────────────────────────────
# Global State
# ─────────────────────────────────────────────
camera      = None
camera_lock = threading.Lock()

current_state = {
    "emotion":       "Neutral",
    "confidence":    0.0,
    "detections":    0,
    "session_start": time.time()
}

# ─────────────────────────────────────────────
# DB Init
# ─────────────────────────────────────────────
init_db()

# ─────────────────────────────────────────────
# User Helpers
# ─────────────────────────────────────────────
def load_users():
    os.makedirs("database", exist_ok=True)
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        default = {"admin": {"password": "admin123", "fullname": "Admin User"}}
        save_users(default)
        return default


def save_users(users):
    os.makedirs("database", exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


# ─────────────────────────────────────────────
# Camera (local only)
# ─────────────────────────────────────────────
def get_camera():
    global camera
    with camera_lock:
        if camera is None or not camera.isOpened():
            camera = cv2.VideoCapture(0)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return camera


def generate_frames():
    """Server-side MJPEG stream — local mode only."""
    cam = get_camera()
    while True:
        with camera_lock:
            success, frame = cam.read()
        if not success:
            time.sleep(0.05)
            continue

        emotion, confidence = predict_emotion(frame)
        if emotion is not None:
            current_state["emotion"]     = emotion
            current_state["confidence"]  = round(confidence * 100, 1)
            current_state["detections"] += 1

            if current_state["detections"] % 10 == 0:
                try:
                    save_emotion(
                        session.get("user", "guest"),
                        emotion,
                        round(confidence * 100, 1)
                    )
                except Exception:
                    pass

            label = f"{emotion.upper()}  {confidence * 100:.1f}%"
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), (0, 0, 0), -1)
            cv2.putText(frame, label, (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )
        time.sleep(0.05)


# ═══════════════════════════════════════════════
# AUTH ROUTES
# ═══════════════════════════════════════════════

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.is_json:
            data     = request.get_json()
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

        users     = load_users()
        user_data = users.get(username)
        if user_data:
            stored = user_data.get("password") if isinstance(user_data, dict) else user_data
        else:
            stored = None

        if stored and stored == password:
            session["user"] = username
            current_state["session_start"] = time.time()
            if request.is_json:
                return jsonify({"status": "ok"})
            return redirect(url_for("dashboard"))

        if request.is_json:
            return jsonify({"status": "error", "message": "Invalid credentials."}), 401
        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data     = request.get_json(silent=True) or {}
        fullname = data.get("fullname", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password or not fullname:
            return jsonify({"status": "error", "message": "All fields required."}), 400

        users = load_users()
        if username in users:
            return jsonify({"status": "error", "message": "Username already exists."}), 409

        users[username] = {"password": password, "fullname": fullname}
        try:
            save_users(users)
            return jsonify({"status": "ok", "message": "Account created successfully."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/guest")
def guest():
    session["user"] = "guest"
    current_state["session_start"] = time.time()
    return redirect(url_for("dashboard"))


# ═══════════════════════════════════════════════
# MAIN PAGES
# ═══════════════════════════════════════════════

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html",
                           user=session["user"],
                           is_cloud=IS_CLOUD)


# ═══════════════════════════════════════════════
# VIDEO FEED (local only)
# ═══════════════════════════════════════════════

@app.route("/video_feed")
def video_feed():
    if IS_CLOUD:
        return jsonify({"error": "Camera not available on cloud"}), 404
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# ═══════════════════════════════════════════════
# BROWSER WEBCAM — cloud mode
# ═══════════════════════════════════════════════

@app.route("/predict_frame", methods=["POST"])
def predict_frame():
    try:
        data     = request.get_json(silent=True) or {}
        img_data = data.get("image", "")

        if not img_data:
            return jsonify({"error": "No image data"}), 400

        if "," in img_data:
            img_data = img_data.split(",")[1]

        img_bytes = base64.b64decode(img_data)
        np_arr    = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Invalid image"}), 400

        emotion, confidence = predict_emotion(frame)

        if emotion is None:
            emotion    = "Neutral"
            confidence = 0.0

        current_state["emotion"]     = emotion
        current_state["confidence"]  = round(float(confidence) * 100, 1)
        current_state["detections"] += 1

        print(f"[predict_frame] {emotion} — {confidence*100:.1f}%")

        if current_state["detections"] % 10 == 0:
            try:
                save_emotion(
                    session.get("user", "guest"),
                    emotion,
                    round(float(confidence) * 100, 1)
                )
            except Exception:
                pass

        return jsonify({
            "emotion":    emotion,
            "confidence": round(float(confidence), 4),
            "detections": current_state["detections"]
        })

    except Exception as e:
        print(f"[predict_frame error] {e}")
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════
# EMOTION API
# ═══════════════════════════════════════════════

@app.route("/get_emotion")
def get_emotion():
    elapsed = int(time.time() - current_state["session_start"])
    return jsonify({
        "emotion":        current_state["emotion"],
        "confidence":     current_state["confidence"] / 100,
        "detections":     current_state["detections"],
        "session_time":   f"{elapsed//60:02d}:{elapsed%60:02d}",
        "recommendation": get_recommendation(current_state["emotion"])
    })


# ═══════════════════════════════════════════════
# ENRICHMENT API
# ═══════════════════════════════════════════════

@app.route("/api/enrich", methods=["POST"])
def enrich():
    data       = request.get_json(silent=True) or {}
    emotion    = data.get("emotion",    "neutral").lower()
    confidence = float(data.get("confidence", 0.0))

    results = {}

    def fetch_videos():  results["videos"]    = get_study_videos(emotion)
    def fetch_advice():  results["ai_advice"] = get_ai_study_advice(emotion, confidence)
    def fetch_quote():   results["quote"]     = get_motivational_quote(emotion)

    threads = [
        threading.Thread(target=fetch_videos),
        threading.Thread(target=fetch_advice),
        threading.Thread(target=fetch_quote),
    ]
    for t in threads: t.start()
    for t in threads: t.join(timeout=10)

    return jsonify({
        "videos":    results.get("videos",    []),
        "ai_advice": results.get("ai_advice", None),
        "quote":     results.get("quote",     {"quote": "Keep going.", "author": "Unknown"}),
    })


# ═══════════════════════════════════════════════
# SAVE SESSION
# ═══════════════════════════════════════════════

@app.route("/save_session", methods=["POST"])
def save_session_route():
    try:
        save_emotion(
            session.get("user", "guest"),
            current_state["emotion"],
            current_state["confidence"]
        )
        return jsonify({"status": "saved"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ═══════════════════════════════════════════════
# HISTORY & ANALYTICS
# ═══════════════════════════════════════════════

@app.route("/get_history")
def history():
    try:
        rows = get_history(session.get("user", "guest"))
        return jsonify({"history": rows})
    except Exception as e:
        return jsonify({"history": [], "error": str(e)})


@app.route("/get_emotion_counts")
def emotion_counts():
    try:
        counts = get_emotion_counts(session.get("user", "guest"))
        return jsonify(counts)
    except Exception:
        return jsonify({})


@app.route("/get_emotion_meter")
def get_emotion_meter():
    emotions = ["happy", "sad", "neutral", "angry", "surprise", "disgust", "fear"]
    meter    = {e: 0.0 for e in emotions}
    current  = current_state["emotion"].lower()
    if current in meter:
        meter[current] = current_state["confidence"]
    return jsonify(meter)


# ═══════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════

@app.route("/health")
def health():
    return jsonify({
        "status":  "running",
        "mode":    "cloud" if IS_CLOUD else "local",
        "emotion": current_state["emotion"],
        "uptime":  int(time.time() - current_state["session_start"])
    })

@app.route("/warmup")
def warmup():
    import numpy as np
    dummy = np.zeros((224, 224, 3), dtype=np.uint8)
    predict_emotion(dummy)
    return "Model warmed up"


# ═══════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════

import atexit

@atexit.register
def release_camera():
    global camera
    if camera and camera.isOpened():
        camera.release()


# ═══════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print(f"  EmoStudyAI — {'CLOUD' if IS_CLOUD else 'LOCAL'} mode")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(
        host        = "0.0.0.0",
        port        = int(os.environ.get("PORT", 5000)),
        debug       = False,
        threaded    = True,
        use_reloader= False
    )