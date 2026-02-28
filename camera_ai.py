"""
AI-камера для EcoSchool Dashboard
Запускать отдельно: python camera_ai.py

Требования:
    pip install opencv-python ultralytics requests

Скрипт детектирует людей через YOLOv8 и шлёт статус
на Django-сервер каждую секунду.
"""

import cv2
import time
import requests
from ultralytics import YOLO

# ── Настройки ────────────────────────────────────────────
DJANGO_URL    = "http://127.0.0.1:8000/api/classroom/"
CLASSROOM     = "Каб. 101"          # <- название кабинета как в БД
LIGHT_OFF_DELAY = 10                # секунд без людей → LIGHT OFF
SEND_INTERVAL   = 1.0               # как часто слать статус (сек)

# ── Инициализация ────────────────────────────────────────
model = YOLO("yolov8n.pt")
cap   = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

no_person_timer = None
last_sent       = 0


def send_status(person_detected: bool, status: str):
    """Отправить статус на Django. Не падает если сервер недоступен."""
    try:
        requests.post(
            DJANGO_URL,
            json={
                "classroom":       CLASSROOM,
                "person_detected": person_detected,
                "status":          status,
            },
            timeout=1,
        )
    except Exception:
        pass   # Сервер может быть недоступен — не останавливаем скрипт


print(f"[EcoSchool AI] Камера запущена. Кабинет: {CLASSROOM}")
print(f"[EcoSchool AI] Статус будет отправляться на {DJANGO_URL}")
print("[EcoSchool AI] Нажми ESC или Q для выхода\n")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[EcoSchool AI] Ошибка камеры")
            break

        results = model(frame, verbose=False)
        person_detected = False

        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                if model.names[cls] == "person":
                    person_detected = True
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 128), 2)
                    cv2.putText(frame, "PERSON", (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 128), 2)

        # ── Логика света ──────────────────────────────────
        if person_detected:
            no_person_timer = None
            status = "on"
            label  = "LIGHT ON"
            color  = (0, 255, 128)
        else:
            if no_person_timer is None:
                no_person_timer = time.time()
            elapsed = time.time() - no_person_timer
            if elapsed > LIGHT_OFF_DELAY:
                status = "off"
                label  = "LIGHT OFF"
                color  = (80, 80, 80)
            else:
                status = "waiting"
                label  = f"WAITING... {int(elapsed)}/{LIGHT_OFF_DELAY}s"
                color  = (0, 200, 255)

        # ── Отрисовка ─────────────────────────────────────
        # Полупрозрачная плашка внизу
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, frame.shape[0] - 60), (frame.shape[1], frame.shape[0]),
                      (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        cv2.putText(frame, label, (20, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        cv2.putText(frame, CLASSROOM, (20, 36),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # ── Отправка статуса на сервер ────────────────────
        now = time.time()
        if now - last_sent >= SEND_INTERVAL:
            send_status(person_detected, status)
            last_sent = now
            print(f"[{time.strftime('%H:%M:%S')}] {CLASSROOM} → {label}")

        cv2.imshow("EcoSchool AI — " + CLASSROOM, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord("q"):
            break

except KeyboardInterrupt:
    print("\n[EcoSchool AI] Остановлено пользователем")

finally:
    # Отправляем финальный статус — свет выключен
    send_status(False, "off")
    cap.release()
    cv2.destroyAllWindows()
    print("[EcoSchool AI] Камера закрыта корректно")
