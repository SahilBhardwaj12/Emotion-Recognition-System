from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session
from flask_cors import CORS
import cv2
import threading
import time
import json
import os
from datetime import datetime

from utils.predict        import predict_emotion
from utils.recommendation import get_recommendation
from utils.database       import init_db, save_emotion, get_history, get_emotion_counts
from utils.youtube_api    import get_study_videos
from utils.gemini_api     import get_ai_study_advice
from utils.quotes_api     import get_motivational_quote

app = Flask(__name__)
app.secret_key = "emostudyai_secret_key_2024"
CORS(app)

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
            break

        emotion, confidence = predict_emotion(frame)

        if emotion is not None:
            current_state["emotion"]     = emotion
            current_state["confidence"]  = round(confidence * 100, 1)
            current_state["detections"] += 1

            label = f"{emotion.upper()}  {confidence * 100:.1f}%"
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), (0, 0, 0), -1)
            cv2.putText(frame, label, (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               buffer.tobytes() + b'\r\n')

        time.sleep(0.05)


# ─────────────────────────────────────────────
# Auth Routes
# ─────────────────────────────────────────────
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Support both JSON (from login.js) and form submissions
        if request.is_json:
            data     = request.get_json() or {}
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
        else:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()

        try:
            with open('database/users.json', 'r') as f:
                users = json.load(f)
        except Exception:
            users = {}

        user_data = users.get(username)
        valid = False
        if isinstance(user_data, dict):
            valid = user_data.get('password') == password
        elif isinstance(user_data, str):
            valid = user_data == password

        if valid:
            session['user'] = username
            session['name'] = user_data.get('name', username) if isinstance(user_data, dict) else username
            current_state["session_start"] = time.time()
            if request.is_json:
                return jsonify({"status": "ok"})
            return redirect(url_for('dashboard'))
        else:
            if request.is_json:
                return jsonify({"status": "error", "message": "Invalid username or password"}), 401
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():
    data     = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    fullname = data.get('fullname', '').strip()

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password required"}), 400

    try:
        with open('database/users.json', 'r') as f:
            users = json.load(f)
    except Exception:
        users = {}

    if username in users:
        return jsonify({"status": "error", "message": "Username already exists"}), 400

    users[username] = {"password": password, "name": fullname or username}

    with open('database/users.json', 'w') as f:
        json.dump(users, f, indent=2)

    return jsonify({"status": "ok"})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/guest')
def guest():
    session['user'] = 'guest'
    session['name'] = 'Guest'
    current_state["session_start"] = time.time()
    return redirect(url_for('dashboard'))


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html',
                           user=session.get('user'),
                           name=session.get('name', 'User'))


# ─────────────────────────────────────────────
# Video Feed
# ─────────────────────────────────────────────
@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


# ─────────────────────────────────────────────
# Emotion API
# ─────────────────────────────────────────────
@app.route('/get_emotion')
def get_emotion():
    elapsed = int(time.time() - current_state["session_start"])
    minutes = elapsed // 60
    seconds = elapsed % 60

    recommendation = get_recommendation(current_state["emotion"])

    return jsonify({
        "emotion":        current_state["emotion"],
        "confidence":     current_state["confidence"] / 100,  # send as 0-1
        "detections":     current_state["detections"],
        "session_time":   f"{minutes:02d}:{seconds:02d}",
        "recommendation": recommendation
    })


# ─────────────────────────────────────────────
# Enrichment API
# ─────────────────────────────────────────────
@app.route('/api/enrich', methods=['POST'])
def enrich():
    data       = request.get_json() or {}
    emotion    = data.get('emotion', 'neutral')
    confidence = data.get('confidence', 0.0)  # 0-1 from frontend

    videos = get_study_videos(emotion)
    advice = get_ai_study_advice(emotion, confidence)
    quote  = get_motivational_quote(emotion)

    return jsonify({
        "videos":    videos,
        "ai_advice": advice,
        "quote":     quote
    })


# ─────────────────────────────────────────────
# Save Session
# ─────────────────────────────────────────────
@app.route('/save_session', methods=['POST'])
def save_session():
    try:
        emotion = current_state["emotion"]
        conf    = current_state["confidence"] / 100
        save_emotion(emotion, conf)
        return jsonify({"status": "saved", "emotion": emotion})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────
# History
# ─────────────────────────────────────────────
@app.route('/get_history')
def get_history_route():
    try:
        history = get_history()
        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"history": [], "error": str(e)})


@app.route('/get_emotion_counts')
def get_counts():
    try:
        counts = get_emotion_counts()
        return jsonify(counts)
    except Exception as e:
        return jsonify({})


# ─────────────────────────────────────────────
# Emotion Meter
# ─────────────────────────────────────────────
@app.route('/get_emotion_meter')
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
@app.route('/get_study_tips')
def get_study_tips():
    tips = {
        "happy":    ["Use this energy to tackle your hardest subject.", "Try teaching the concept to someone else.", "Set ambitious goals for today's session."],
        "sad":      ["Start with easy, familiar topics.", "Take short breaks every 20 minutes.", "Listen to calm instrumental music."],
        "neutral":  ["This is your prime focus window.", "Try Pomodoro: 25 min on, 5 min off.", "Set a specific goal for the next 30 minutes."],
        "angry":    ["Take 5 deep breaths before starting.", "Do a 10-minute walk to reset.", "Choose a simple repetitive task."],
        "surprise": ["Channel this energy into a new topic.", "Write down 3 things you want to learn.", "Try mind-mapping your subject."],
        "disgust":  ["Break your task into smallest steps.", "Reward yourself after each milestone.", "Switch your study environment."],
        "fear":     ["Write down exactly what you're worried about.", "Focus only on what you can control.", "Review past successes to rebuild confidence."]
    }
    return jsonify(tips)


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({
        "status":  "running",
        "user":    session.get('user', 'none'),
        "emotion": current_state["emotion"],
        "uptime":  int(time.time() - current_state["session_start"])
    })


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("  EmoStudyAI Server Starting...")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True,
        use_reloader=False
    )