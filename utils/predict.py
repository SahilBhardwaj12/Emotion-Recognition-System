import os
import cv2
import numpy as np
import requests
import gc

model        = None
face_cascade = None

emotion_labels       = ["Surprise", "Fear", "Disgust", "Happy", "Sad", "Angry", "Neutral"]
CONFIDENCE_THRESHOLD = 0.25  # lowered for better detection

MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "model", "best_model.pth")
)


# ─────────────────────────────────────────────
# MODEL DOWNLOAD (fallback for cloud)
# ─────────────────────────────────────────────
def _download_from(url, label):
    try:
        print(f"[Model] ⬇️  Trying {label}...", flush=True)
        headers  = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, stream=True, timeout=300)

        if response.status_code != 200:
            print(f"[Model] ❌ {label} returned HTTP {response.status_code}", flush=True)
            return False

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        if size_mb < 1:
            print(f"[Model] ❌ {label} too small ({size_mb:.2f} MB)", flush=True)
            os.remove(MODEL_PATH)
            return False

        print(f"[Model] ✅ {label} downloaded ({size_mb:.1f} MB)", flush=True)
        return True

    except Exception as e:
        print(f"[Model] ❌ {label} failed: {e}", flush=True)
        return False


def _ensure_model():
    if os.path.exists(MODEL_PATH):
        size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        if size_mb > 1:
            print(f"[Model] ✅ Found ({size_mb:.1f} MB)", flush=True)
            return True
        else:
            print(f"[Model] ⚠️  Too small ({size_mb:.2f} MB) — re-downloading...", flush=True)
            os.remove(MODEL_PATH)

    print("[Model] ❌ Model not found — no download sources configured.", flush=True)
    return False


# ─────────────────────────────────────────────
# LOAD RESOURCES
# ─────────────────────────────────────────────

def load_resources():
    global model, face_cascade

    if face_cascade is None:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        print("[Face] ✅ Cascade loaded", flush=True)

    if model is None:
        import torch
        import torch.nn as nn
        from torchvision import models as tvm

        if not _ensure_model():
            return

        try:
            net = tvm.mobilenet_v2(weights=None)
            net.classifier = nn.Sequential(
                nn.Dropout(0.4),
                nn.Linear(net.classifier[1].in_features, 7),
            )
            net.load_state_dict(
                torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
            )
            net.eval()
            model = net
            print("[INFO] ✅ MobileNetV2 loaded successfully.", flush=True)

        except Exception as e:
            print(f"[Model] ❌ Load failed: {e}", flush=True)

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
        print(f"[predict_emotion error] {e}", flush=True)
        return None, None