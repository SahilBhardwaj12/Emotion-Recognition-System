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