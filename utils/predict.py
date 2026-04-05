import os
import cv2
import numpy as np
import requests

model = None
face_cascade = None

emotion_labels = ["Surprise", "Fear", "Disgust", "Happy", "Sad", "Angry", "Neutral"]
CONFIDENCE_THRESHOLD = 0.40

MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "model", "best_model.pth")
)

# ✅ ONLY FILE ID (NOT full link)
GDRIVE_ID = "1KAQISsqJ3wpIMdyjL3jsklSkl-m21BJC"


# ─────────────────────────────
# DOWNLOAD MODEL (FIXED)
# ─────────────────────────────
def _ensure_model():
    if os.path.exists(MODEL_PATH):
        size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        if size_mb > 20:
            print(f"[Model] Found ({size_mb:.1f} MB) ✅")
            return True
        else:
            os.remove(MODEL_PATH)

    print("[Model] ⬇️ Downloading from Google Drive...")

    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def save_response_content(response, destination):
        with open(destination, "wb") as f:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)

    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()

    response = session.get(URL, params={"id": GDRIVE_ID}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {"id": GDRIVE_ID, "confirm": token}
        response = session.get(URL, params=params, stream=True)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    save_response_content(response, MODEL_PATH)

    size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
    print(f"[Model] Downloaded size: {size_mb:.1f} MB")

    return size_mb > 20


# ─────────────────────────────
# LOAD MODEL
# ─────────────────────────────
def load_resources():
    global model, face_cascade

    if face_cascade is None:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    if model is None:
        import torch
        import torch.nn as nn
        from torchvision import models as tv_models

        if not _ensure_model():
            print("[Model] ❌ Download failed")
            return

        try:
            print("[Model] Loading ResNet50...")

            net = tv_models.resnet50(weights=None)
            net.fc = nn.Sequential(
                nn.Dropout(0.4),
                nn.Linear(net.fc.in_features, 7),
            )

            net.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
            net.eval()

            model = net
            print("[Model] ✅ Loaded successfully")

        except Exception as e:
            print(f"[Model Error] {e}")
            model = None


# ─────────────────────────────
# PREDICT
# ─────────────────────────────
def predict_emotion(frame):
    load_resources()

    if model is None or face_cascade is None:
        return None, None

    try:
        import torch
        from torchvision import transforms

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray, 1.3, 5, minSize=(30, 30)
        )

        if len(faces) == 0:
            return None, None

        # largest face
        faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
        x, y, w, h = faces[0]

        face = frame[y:y+h, x:x+w]
        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)

        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406],
                                 [0.229, 0.224, 0.225]),
        ])

        face_tensor = transform(face).unsqueeze(0)

        with torch.no_grad():
            output = model(face_tensor)
            probs = torch.softmax(output, dim=1)

            confidence = float(probs.max().item())
            idx = int(probs.argmax().item())

        emotion = emotion_labels[idx] if confidence >= CONFIDENCE_THRESHOLD else "Neutral"

        return emotion, confidence

    except Exception as e:
        print(f"[Predict Error] {e}")
        return None, None