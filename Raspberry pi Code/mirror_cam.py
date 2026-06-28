import cv2
import face_recognition
import requests
import numpy as np
from datetime import datetime, timedelta
from tensorflow.keras.models import load_model
import time

# Load models
face_model = load_model("mobilenetv2_face_recognition.h5")
emotion_model = load_model("emotion_model_mobilenetv2.h5")

# Mappings
face_map = {0: "suvan", 1: "sundar"}
emotion_map = {0: "happy", 1: "sad", 2: "angry"}

def send_to_backend(status, image_path=None, emotion=None):
    url = "https://0a89-2400-1a00-b030-b23f-49a5-fd84-5ab2-ce33.ngrok-free.app/api/mirror-feed/"  # Replace with actual IP
    files = {'image': open(image_path, 'rb')} if image_path else None
    data = {'status': status, 'emotion': emotion}

    print(f"[SENDING TO BACKEND] Status: {status}, Emotion: {emotion}")
    if image_path:
        print(f"[INFO] Image Path Sent: {image_path}")

    try:
        response = requests.post(url, files=files, data=data)
        print(f"[RESPONSE] {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] Failed to send data: {e}")

# Initialize webcam
cap = cv2.VideoCapture(0)
print("[INFO] Webcam feed running...")

# Timers
last_detected_time = datetime.min
last_no_face_time = datetime.min
DETECTION_COOLDOWN = timedelta(seconds=20)
NO_FACE_COOLDOWN = timedelta(seconds=3)

last_status = None

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    cv2.imshow("Smart Mirror", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)

    now = datetime.now()

    if face_locations:
        if now - last_detected_time >= DETECTION_COOLDOWN:
            for top, right, bottom, left in face_locations:
                face_img = frame[top:bottom, left:right]
                face_resized = cv2.resize(face_img, (224, 224))
                face_array = np.expand_dims(face_resized, axis=0) / 255.0

                face_pred = face_model.predict(face_array)
                identity_index = np.argmax(face_pred)
                confidence = face_pred[0][identity_index]

                if confidence > 0.8:
                    identity = face_map[identity_index]

                    emo_face = cv2.resize(face_img, (224, 224))
                    emo_input = np.expand_dims(emo_face, axis=0) / 255.0
                    emo_pred = emotion_model.predict(emo_input)
                    emotion = emotion_map[np.argmax(emo_pred)]

                    print(f"[DETECTED] Face: {identity} | Emotion: {emotion} | Confidence: {confidence:.2f}")
                    send_to_backend(status=identity, emotion=emotion)
                    last_status = (identity, emotion)
                    last_detected_time = now
                else:
                    print("[DETECTED] Unknown face detected.")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    path = f"/home/pi/unknown_{timestamp}.jpg"
                    cv2.imwrite(path, frame)
                    send_to_backend(status="unknown", image_path=path)
                    last_status = "unknown"
                    last_detected_time = now
    else:
        if now - last_no_face_time >= NO_FACE_COOLDOWN:
            print("[INFO] No face detected.")
            send_to_backend(status="no_face")
            last_status = "no_face"
            last_no_face_time = now

cap.release()
cv2.destroyAllWindows()
