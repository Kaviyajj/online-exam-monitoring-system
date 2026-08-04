import csv
from datetime import datetime

def log_event(candidate_id, event_type, absence_duration, remarks):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("eventlog.csv", "r", newline="") as file:
        rows = list(csv.reader(file))
        event_id = len(rows)
    with open("eventlog.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            event_id,
            candidate_id,
            event_type,
            timestamp,
            absence_duration,
            remarks
        ])
print("Event Log CSV is ready.")