import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import cv2
import numpy as np

model = None
face_cascade = None

emotion_labels = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]

def load_resources():
    global model, face_cascade

    if face_cascade is None:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    if model is None:
        model_path = os.path.join(os.path.dirname(__file__), "..", "model", "emotion_model.h5")
        if os.path.exists(model_path):
            from tensorflow.keras.models import load_model
            model = load_model(model_path)
        else:
            print(f"[WARN] Model not found at {model_path}")

def predict_emotion(frame):
    load_resources()

    if model is None or face_cascade is None:
        return None, None

    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            return None, None

        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        x, y, w, h = faces[0]

        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (48, 48))
        face = face / 255.0
        face = np.reshape(face, (1, 48, 48, 1))

        prediction = model.predict(face, verbose=0)
        emotion_index = int(np.argmax(prediction))
        emotion = emotion_labels[emotion_index]
        confidence = float(np.max(prediction))

        return emotion, confidence

    except Exception as e:
        print(f"[predict_emotion error] {e}")
        return None, None