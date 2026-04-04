
import os
import cv2
import numpy as np

model = None
face_cascade = None


emotion_labels = ["Surprise", "Fear", "Disgust", "Happy", "Sad", "Angry", "Neutral"]


CONFIDENCE_THRESHOLD = 0.40

def load_resources():
    global model, face_cascade

    if face_cascade is None:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    if model is None:
        import torch
        import torch.nn as nn
        from torchvision import models

        model_path = os.path.join(os.path.dirname(__file__), "..", "model", "best_model.pth")
        if os.path.exists(model_path):
            # Build same ResNet50 architecture used in training
            net = models.resnet50(weights=None)
            net.fc = nn.Sequential(
                nn.Dropout(0.4),
                nn.Linear(net.fc.in_features, 7),
            ) 
            net.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
            net.eval()
            model = net
            print("[INFO] Model loaded successfully.")
        else:
            print(f"[WARN] Model not found at {model_path}")


def predict_emotion(frame):
    load_resources()

    if model is None or face_cascade is None:
        return None, None

    try:
        import torch
        from torchvision import transforms

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30)
        )

        if len(faces) == 0:
            return None, None

        
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        x, y, w, h = faces[0]

        
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

        face_tensor = transform(face).unsqueeze(0)   # (1, 3, 224, 224)

        with torch.no_grad():
            output     = model(face_tensor)
            probs      = torch.softmax(output, dim=1)
            confidence = float(probs.max().item())
            emotion_index = int(probs.argmax().item())

        if confidence < CONFIDENCE_THRESHOLD:
            emotion = "Neutral"
        else:
            emotion = emotion_labels[emotion_index]

        return emotion, confidence

    except Exception as e:
        print(f"[predict_emotion error] {e}")
        return None, None

