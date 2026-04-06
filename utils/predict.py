import os
import cv2
import numpy as np
import requests

model        = None
face_cascade = None

emotion_labels       = ["Surprise", "Fear", "Disgust", "Happy", "Sad", "Angry", "Neutral"]
CONFIDENCE_THRESHOLD = 0.40

MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "model", "best_model.pth")
)

# GitHub Release URL — direct download, no redirect, no virus warning
MODEL_URL = "https://github.com/SahilBhardwaj12/Emotion-Recognition-System/releases/download/v1.0/best_model.pth"

# Hugging Face fallback
HF_URL = "https://huggingface.co/rishav21424/emostudyai-model/resolve/main/best_model.pth"


# ─────────────────────────────────────────────
# MODEL DOWNLOAD
# ─────────────────────────────────────────────
def _download_from(url, label):
    """Download model from a URL. Returns True if successful."""
    try:
        print(f"[Model] ⬇️  Trying {label}...")
        headers  = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, stream=True, timeout=300)

        if response.status_code != 200:
            print(f"[Model] ❌ {label} returned HTTP {response.status_code}")
            return False

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        if size_mb < 10:
            print(f"[Model] ❌ {label} downloaded too small ({size_mb:.2f} MB)")
            os.remove(MODEL_PATH)
            return False

        print(f"[Model] ✅ {label} downloaded ({size_mb:.1f} MB)")
        return True

    except Exception as e:
        print(f"[Model] ❌ {label} failed: {e}")
        return False


def _ensure_model():
    """Make sure real model file exists. Try GitHub then HuggingFace."""
    if os.path.exists(MODEL_PATH):
        size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        if size_mb > 10:
            print(f"[Model] ✅ Found ({size_mb:.1f} MB)")
            return True
        else:
            print(f"[Model] ⚠️  Too small ({size_mb:.2f} MB) — re-downloading...")
            os.remove(MODEL_PATH)

    # Try GitHub Release first
    if _download_from(MODEL_URL, "GitHub Release"):
        return True

    # Fallback to Hugging Face
    if _download_from(HF_URL, "Hugging Face"):
        return True

    print("[Model] ❌ All download sources failed.")
    return False


# ─────────────────────────────────────────────
# LOAD MODEL
# ─────────────────────────────────────────────
def load_resources():
    global model, face_cascade

    if face_cascade is None:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        print("[Face] ✅ Cascade loaded")

    if model is None:
        import torch
        import torch.nn as nn
        from torchvision import models as tv_models

        if not _ensure_model():
            print("[Model] ❌ Cannot load — no model file.")
            return

        try:
            print("[Model] Loading ResNet50 architecture...")
            net = tv_models.resnet50(weights=None)
            net.fc = nn.Sequential(
                nn.Dropout(0.4),
                nn.Linear(net.fc.in_features, 7),
            )
            net.load_state_dict(
                torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
            )
            net.eval()
            model = net
            print("[Model] ✅ Model loaded and ready!")

        except Exception as e:
            print(f"[Model] ❌ Load failed: {e}")
            model = None


# ─────────────────────────────────────────────
# PREDICT EMOTION
# ─────────────────────────────────────────────
def predict_emotion(frame):
    load_resources()

    if model is None or face_cascade is None:
        return None, None

    try:
        import torch
        from torchvision import transforms

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30)
        )

        if len(faces) == 0:
            return None, None

        # Pick largest face
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        x, y, w, h = faces[0]

        face = frame[y:y+h, x:x+w]
        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)

        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                [0.485, 0.456, 0.406],
                [0.229, 0.224, 0.225]
            ),
        ])

        face_tensor = transform(face).unsqueeze(0)

        with torch.no_grad():
            output        = model(face_tensor)
            probs         = torch.softmax(output, dim=1)
            confidence    = float(probs.max().item())
            emotion_index = int(probs.argmax().item())

        if confidence < CONFIDENCE_THRESHOLD:
            emotion = "Neutral"
        else:
            emotion = emotion_labels[emotion_index]

        return emotion, confidence

    except Exception as e:
        print(f"[predict_emotion error] {e}")
        return None, None