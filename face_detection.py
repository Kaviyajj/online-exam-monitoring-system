import cv2
import time
import csv
import os
from datetime import datetime
monitoring = False
paused = False
face_status = "Detecting..."
face_count = 0
absence_start_time = None
absence_duration = 0
absence_count = 0
face_currently_absent = False
def log_event_csv(candidate_id, event_type, remarks):
    file_path = "eventlog.csv"
    if not os.path.exists(file_path):
        with open(file_path, "w", newline="") as f:
            csv.writer(f).writerow(
                ["Event ID", "Candidate ID", "Event Type", "Timestamp", "Remarks"]
            )
    with open(file_path, "r", newline="") as f:
        event_id = len(list(csv.reader(f)))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_path, "a", newline="") as f:
        csv.writer(f).writerow(
            [event_id, candidate_id, event_type, timestamp, remarks]
        )
def video_stream(candidate_id):
    global monitoring, paused
    global face_status, face_count
    global absence_start_time, absence_duration
    global absence_count, face_currently_absent
    face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
    camera = cv2.VideoCapture(0)
    while monitoring:
        if paused:
            time.sleep(0.1)
            continue
        success, frame = camera.read()
        if not success:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        face_count = len(faces)
        if face_count == 0:
            face_status = "Face Not Detected"
            if not face_currently_absent:
                absence_start_time = time.time()
                absence_count += 1
                face_currently_absent = True
            absence_duration = int(time.time() - absence_start_time)
        else:
            face_status = "Face Detected"
            if face_currently_absent:
                log_event_csv(
                    candidate_id,
                    "Face Not Detected",
                    f"Face absent for {absence_duration} sec"
                )
            face_currently_absent = False
            absence_duration = 0
        # Webcam only shows face status
        cv2.putText(frame, face_status,
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0) if face_status == "Face Detected" else (0, 0, 255),
                    2)
        ret, buffer = cv2.imencode('.jpg', frame)
        yield buffer.tobytes()
    camera.release()