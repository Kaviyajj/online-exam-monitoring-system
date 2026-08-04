import sqlite3
from datetime import datetime

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

cursor.execute("""
INSERT INTO EventLog(candidate_id, event_type, timestamp, remarks)
VALUES (?, ?, ?, ?)
""", (
    1,
    "Exam Started",
    timestamp,
    "Candidate started the examination."
))

conn.commit()
conn.close()

print("Sample event inserted successfully!")