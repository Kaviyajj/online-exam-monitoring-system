import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS Session (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT,
    start_time TEXT,
    end_time TEXT,
    status TEXT
)
""")

conn.commit()
conn.close()

print("Session table created successfully!")