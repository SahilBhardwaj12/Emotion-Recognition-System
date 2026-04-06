from dotenv import load_dotenv
import os

load_dotenv()

from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session
from flask_cors import CORS
import cv2
import threading
import time
import json
import base64
import numpy as np
import torch

torch.set_num_threads(1)

# ─────────────────────────────
# Utils
# ─────────────────────────────
from utils.predict        import predict_emotion
from utils.recommendation import get_recommendation
from utils.database       import init_db, save_emotion, get_history, get_emotion_counts
from utils.youtube_api    import get_study_videos
from utils.gemini_api     import get_ai_study_advice
from utils.quotes_api     import get_motivational_quote

# ─────────────────────────────
# App Setup
# ─────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_key")
CORS(app)

USERS_FILE = "database/users.json"

IS_CLOUD = bool(
    os.environ.get("RAILWAY_ENVIRONMENT") or
    os.environ.get("RENDER") or
    os.environ.get("CLOUD")
)

print(f"RENDER env: {os.environ.get('RENDER')}")
print(f"IS_CLOUD: {IS_CLOUD}")
print(f"[EmoStudyAI] Running in {'CLOUD' if IS_CLOUD else 'LOCAL'} mode")

# ─────────────────────────────
# Global State
# ─────────────────────────────
camera = None
camera_lock = threading.Lock()

current_state = {
    "emotion": "Neutral",
    "confidence": 0.0,
    "detections": 0,
    "session_start": time.time()
}

# ─────────────────────────────
# INIT DB
# ─────────────────────────────
init_db()

# ─────────────────────────────
# USER SYSTEM
# ─────────────────────────────
def load_users():
    os.makedirs("database", exist_ok=True)
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        default = {"admin": {"password": "admin123", "fullname": "Admin"}}
        save_users(default)
        return default


def save_users(users):
    os.makedirs("database", exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

# ─────────────────────────────
# CAMERA
# ─────────────────────────────
def get_camera():
    global camera
    with camera_lock:
        if camera is None or not camera.isOpened():
            camera = cv2.VideoCapture(0)
    return camera


# ─────────────────────────────
# ROUTES
# ─────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", is_cloud=IS_CLOUD)


@app.route("/predict_frame", methods=["POST"])
def predict_frame():
    try:
        data = request.get_json()
        img_data = data.get("image")

        img_data = img_data.split(",")[1]
        img_bytes = base64.b64decode(img_data)

        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        emotion, confidence = predict_emotion(frame)

        if emotion is None:
            emotion, confidence = "Neutral", 0.0

        return jsonify({
            "emotion": emotion,
            "confidence": confidence
        })

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/get_emotion")
def get_emotion():
    return jsonify({
        "emotion": current_state["emotion"],
        "confidence": current_state["confidence"],
        "recommendation": get_recommendation(current_state["emotion"])
    })


@app.route("/api/enrich", methods=["POST"])
def enrich():
    data = request.get_json()
    emotion = data.get("emotion", "neutral")

    return jsonify({
        "videos": get_study_videos(emotion),
        "ai_advice": get_ai_study_advice(emotion, 0.5),
        "quote": get_motivational_quote(emotion)
    })


# ─────────────────────────────
# 🔥 WARMUP (FIXED)
# ─────────────────────────────
def warmup_model():
    try:
        print("[Startup] Warming model...")
        dummy = np.zeros((224, 224, 3), dtype=np.uint8)
        predict_emotion(dummy)
        print("[Startup] Model ready ✅")
    except Exception as e:
        print(f"[Startup Error] {e}")


# ─────────────────────────────
# RUN
# ─────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print(f"EmoStudyAI — {'CLOUD' if IS_CLOUD else 'LOCAL'}")
    print("=" * 50)

    warmup_model()  # ✅ FIXED

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )