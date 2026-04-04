<<<<<<< HEAD
"""
EmoStudyAI — app.py
Complete Flask backend — fully working
"""

from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session
from flask_cors import CORS
import cv2
import threading
import time
import json
import os
from datetime import datetime

# Utils
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
# User Helpers
# ─────────────────────────────────────────────
def load_users():
    """Load users from JSON file. Creates default admin if missing."""
    os.makedirs("database", exist_ok=True)
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        default = {
            "admin": {
                "password": "admin123",
                "fullname": "Admin User"
            }
        }
        save_users(default)
        return default


def save_users(users):
    """Save users dict to JSON file."""
    os.makedirs("database", exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


# ─────────────────────────────────────────────
# Camera
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

            # Save to DB every 10 detections to avoid spam
            if current_state["detections"] % 10 == 0:
                try:
                    user = session.get("user", "guest")
                    save_emotion(user, emotion, round(confidence * 100, 1))
                except Exception:
                    pass

            # Overlay
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
        time.sleep(0.05)  # ~20 FPS


# ─────────────────────────────────────────────
# Auth Routes
# ─────────────────────────────────────────────
@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Support both JSON (fetch) and form POST
        if request.is_json:
            data     = request.get_json()
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

        users = load_users()

        # Support both flat {"user":"pass"} and nested {"user":{"password":"pass"}} formats
        user_data = users.get(username)
        if user_data:
            stored_password = user_data.get("password") if isinstance(user_data, dict) else user_data
        else:
            stored_password = None

        if stored_password and stored_password == password:
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

        # Save new user
        users[username] = {
            "password": password,
            "fullname": fullname
        }
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


# ─────────────────────────────────────────────
# Main Pages
# ─────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])


# ─────────────────────────────────────────────
# Video Feed
# ─────────────────────────────────────────────
@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# ─────────────────────────────────────────────
# Emotion API
# ─────────────────────────────────────────────
@app.route("/get_emotion")
def get_emotion():
    elapsed = int(time.time() - current_state["session_start"])
    minutes = elapsed // 60
    seconds = elapsed % 60

    recommendation = get_recommendation(current_state["emotion"])

    return jsonify({
        "emotion":         current_state["emotion"],
        "confidence":      current_state["confidence"] / 100,
        "detections":      current_state["detections"],
        "session_time":    f"{minutes:02d}:{seconds:02d}",
        "recommendation":  recommendation
    })


# ─────────────────────────────────────────────
# Enrichment API (YouTube + Gemini + Quotes)
# ─────────────────────────────────────────────
@app.route("/api/enrich", methods=["POST"])
def enrich():
    data       = request.get_json(silent=True) or {}
    emotion    = data.get("emotion",    "neutral").lower()
    confidence = float(data.get("confidence", 0.0))

    # Run in parallel for speed
    results = {}

    def fetch_videos():
        results["videos"] = get_study_videos(emotion)

    def fetch_advice():
        results["ai_advice"] = get_ai_study_advice(emotion, confidence)

    def fetch_quote():
        results["quote"] = get_motivational_quote(emotion)

    threads = [
        threading.Thread(target=fetch_videos),
        threading.Thread(target=fetch_advice),
        threading.Thread(target=fetch_quote),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    return jsonify({
        "videos":    results.get("videos",    []),
        "ai_advice": results.get("ai_advice", None),
        "quote":     results.get("quote",     {"quote": "Keep going.", "author": "Unknown"}),
    })


# ─────────────────────────────────────────────
# Save Session
# ─────────────────────────────────────────────
@app.route("/save_session", methods=["POST"])
def save_session_route():
    try:
        user    = session.get("user", "guest")
        emotion = current_state["emotion"]
        conf    = current_state["confidence"]
        save_emotion(user, emotion, conf)
        return jsonify({"status": "saved", "emotion": emotion})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────
# History API
# ─────────────────────────────────────────────
@app.route("/get_history")
def history():
    try:
        user = session.get("user", "guest")
        rows = get_history(user)
        return jsonify({"history": rows})
    except Exception as e:
        return jsonify({"history": [], "error": str(e)})


# ─────────────────────────────────────────────
# Emotion Counts (for analytics charts)
# ─────────────────────────────────────────────
@app.route("/get_emotion_counts")
def emotion_counts():
    try:
        user   = session.get("user", "guest")
        counts = get_emotion_counts(user)
        return jsonify(counts)
    except Exception as e:
        return jsonify({})


# ─────────────────────────────────────────────
# Emotion Meter
# ─────────────────────────────────────────────
@app.route("/get_emotion_meter")
def get_emotion_meter():
    emotions = ["happy", "sad", "neutral", "angry", "surprise", "disgust", "fear"]
    meter    = {e: 0.0 for e in emotions}
    current  = current_state["emotion"].lower()
    if current in meter:
        meter[current] = current_state["confidence"]
    return jsonify(meter)


# ─────────────────────────────────────────────
# Study Tips
# ─────────────────────────────────────────────
@app.route("/get_study_tips")
def get_study_tips():
    tips = {
        "happy":    ["Use this energy to tackle your hardest subject.", "Try teaching the concept to someone else.", "Set ambitious goals for today's session."],
        "sad":      ["Start with easy familiar topics to build momentum.", "Take short breaks every 20 minutes.", "Listen to calm instrumental music while studying."],
        "neutral":  ["This is your prime focus window — use it well.", "Try the Pomodoro technique: 25 min on, 5 min off.", "Set a specific goal for the next 30 minutes."],
        "angry":    ["Take 5 deep breaths before starting.", "Do a 10-minute walk to reset your mind.", "Choose a simple repetitive task like flashcard review."],
        "surprise": ["Channel this energy into exploring a new topic.", "Write down 3 things you want to learn today.", "Try mind-mapping your current subject."],
        "disgust":  ["Break your task into the smallest possible steps.", "Reward yourself after each small milestone.", "Switch your study environment for a fresh perspective."],
        "fear":     ["Write down exactly what you are worried about.", "Focus only on what you can control right now.", "Review past successes to rebuild confidence."]
    }
    return jsonify(tips)


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({
        "status":  "running",
        "user":    session.get("user", "none"),
        "emotion": current_state["emotion"],
        "uptime":  int(time.time() - current_state["session_start"])
    })


# ─────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────
import atexit

@atexit.register
def release_camera():
    global camera
    if camera and camera.isOpened():
        camera.release()


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("  EmoStudyAI Server Starting...")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(
        host        = "0.0.0.0",
        port        = 5000,
        debug       = True,
        threaded    = True,
        use_reloader= False  # prevent double camera init
    )
=======
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import cv2
import threading
import time
from flask import Flask, render_template, Response, jsonify

from utils.predict import predict_emotion
from utils.recommendation import get_recommendation
from utils.youtube_api import get_study_videos
from utils.database import save_emotion, get_history, get_emotion_counts

app = Flask(__name__)

# ── Shared state ────────────────────────────────────────────────────────────
state_lock = threading.Lock()
latest = {
    "emotion": "neutral",
    "confidence": 0.0,
    "frame_count": 0
}

camera = None
camera_lock = threading.Lock()

def get_camera():
    global camera
    with camera_lock:
        if camera is None or not camera.isOpened():
            camera = cv2.VideoCapture(0)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return camera

# ── Save to DB every 10 seconds (background thread) ─────────────────────────
def db_saver():
    while True:
        time.sleep(10)
        with state_lock:
            emotion = latest["emotion"]
            confidence = latest["confidence"]
        if emotion and emotion != "neutral":
            save_emotion(emotion, confidence)

threading.Thread(target=db_saver, daemon=True).start()

# ── Frame generator ──────────────────────────────────────────────────────────
def generate_frames():
    cam = get_camera()
    frame_skip = 0

    while True:
        success, frame = cam.read()
        if not success:
            time.sleep(0.05)
            continue

        frame_skip += 1

        # Run prediction every 3rd frame for performance
        if frame_skip % 3 == 0:
            emotion, confidence = predict_emotion(frame)
            if emotion is not None:
                with state_lock:
                    latest["emotion"] = emotion
                    latest["confidence"] = confidence
                    latest["frame_count"] += 1

        # Draw overlay
        with state_lock:
            display_emotion = latest["emotion"]
            display_conf = latest["confidence"]

        label = f"{display_emotion.upper()}  {display_conf*100:.0f}%"

        # Background bar
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 55), (0, 0, 0), -1)
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 55), (37, 99, 235), 2)

        # Emotion text
        cv2.putText(frame, label, (15, 37),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# ── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/video")
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/emotion")
def emotion():
    with state_lock:
        emotion_val = latest["emotion"]
        confidence_val = latest["confidence"]

    rec = get_recommendation(emotion_val)
    videos = get_study_videos(rec["video_query"])

    return jsonify({
        "emotion": emotion_val,
        "confidence": round(confidence_val * 100, 1),
        "message": rec["message"],
        "tips": rec["tips"],
        "videos": videos
    })

@app.route("/history")
def history():
    return jsonify({
        "history": get_history(20),
        "counts": get_emotion_counts()
    })

@app.route("/save", methods=["POST"])
def save():
    with state_lock:
        emotion_val = latest["emotion"]
        confidence_val = latest["confidence"]
    if emotion_val:
        save_emotion(emotion_val, confidence_val)
    return jsonify({"status": "saved"})

if __name__ == "__main__":
    try:
        print("Starting EmotionStudySystem...")
        print("Open browser at: http://localhost:5000")
        app.run(debug=False, threaded=True, host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("Press Enter to exit...")
>>>>>>> 50806243a990f5276a5517268c84289a1eccefbd
