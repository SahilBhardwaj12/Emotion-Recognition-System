import os
import cv2
import numpy as np

model        = None
face_cascade = None

emotion_labels     = ["Surprise", "Fear", "Disgust", "Happy", "Sad", "Angry", "Neutral"]
CONFIDENCE_THRESHOLD = 0.40
MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "model", "best_model.pth")
)
GDRIVE_ID = "https://drive.google.com/file/d/1KAQISsqJ3wpIMdyjL3jsklSkl-m21BJC/view?usp=sharing"


def _ensure_model():
    """
    Makes sure the real model file exists.
    - If missing → download from Google Drive
    - If tiny (LFS pointer) → delete and re-download
    """
    if os.path.exists(MODEL_PATH):
        size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        if size_mb > 10:
            print(f"[Model] Found real model ({size_mb:.1f} MB) ✅")
            return True
        else:
            print(f"[Model] File too small ({size_mb:.2f} MB) — LFS pointer detected, re-downloading...")
            os.remove(MODEL_PATH)

    # Download from Google Drive
    print("[Model] ⬇️  Downloading from Google Drive...")
    try:
        import gdown
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        gdown.download(
            f"https://drive.google.com/uc?id={GDRIVE_ID}",
            MODEL_PATH,
            quiet=False,
            fuzzy=True
        )
        size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        print(f"[Model] ✅ Downloaded successfully ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"[Model] ❌ Download failed: {e}")
        return False


def load_resources():
    global model, face_cascade

    # Face detector
    if face_cascade is None:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    # Model
    if model is None:
        import torch
        import torch.nn as nn
        from torchvision import models as tv_models

        # Ensure real model file exists
        if not _ensure_model():
            print("[Model] ❌ Cannot load model — file unavailable.")
            return

        try:
            print("[Model] Loading ResNet50...")
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
            print("[Model] ✅ Model loaded and ready.")
        except Exception as e:
            print(f"[Model] ❌ Load failed: {e}")


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

        # Crop and convert
        face = frame[y:y+h, x:x+w]
        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)

        # Preprocess — same as training
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406],
                                 [0.229, 0.224, 0.225]),
        ])

        face_tensor = transform(face).unsqueeze(0)  # (1, 3, 224, 224)

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