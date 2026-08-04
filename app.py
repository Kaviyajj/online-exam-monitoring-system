import face_detection
from flask import Flask, render_template, request, redirect, session
import sqlite3
import re
import base64
from datetime import datetime
from flask import Response
app = Flask(__name__)
app.secret_key = "online_exam_secret"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  
# Event Log Function
def generate_frames(candidate_id):
    for frame in face_detection.video_stream(candidate_id):
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
@app.route("/video_feed")
def video_feed():
    if "candidate_id" not in session:
        return redirect("/login")
    candidate_id = session["candidate_id"]
    return Response(generate_frames(candidate_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route("/exam")
def exam():
    if "candidate_id" not in session:
        return redirect("/login")
    return render_template("exam.html",name=session["candidate_name"])
def log_event(candidate_id, event_type, remarks):
    #  SQLite
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO EventLog(candidate_id, event_type, timestamp, remarks)
        VALUES (?, ?, ?, ?)
    """, (candidate_id, event_type, timestamp, remarks))
    conn.commit()
    conn.close()
    #  CSV
    face_detection.log_event_csv(candidate_id, event_type, remarks)
# Home
@app.route("/")
def home():
    return render_template("index.html")
# Registration Page
@app.route("/register")
def register_page():
    return render_template("register.html")
# Register Candidate
@app.route("/register", methods=["POST"])
def register():
    candidate_id = request.form["candidate_id"].strip()
    name = request.form["name"].strip()
    email = request.form["email"].strip()
    password = request.form["password"].strip()
    photo_data = request.form.get("photo_data")
    if candidate_id == "" or name == "" or email == "" or password == "":
        return render_template(
            "register.html",
            message="All fields are required."
        )
    email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    if not re.match(email_pattern, email):
        return render_template(
            "register.html",
            message="Please enter a valid email."
        )
    if not photo_data:
        return render_template(
            "register.html",
            message="Please capture your photo before registering."
        )
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Candidate WHERE email=?",
        (email,)
    )
    if cursor.fetchone():
        conn.close()
        return render_template(
            "register.html",
            message="Email already registered."
        )
    #  Decode base64 image
    image_data = re.sub('^data:image/.+;base64,', '', photo_data)
    image_bytes = base64.b64decode(image_data)
    photo_path = f"photos/{candidate_id}.png"
    with open(photo_path, "wb") as f:
        f.write(image_bytes)
    try:
        cursor.execute("""
            INSERT INTO Candidate(candidate_id,name,email,password,photo_path)
            VALUES(?,?,?,?,?)
        """, (
            candidate_id,
            name,
            email,
            password,
            photo_path
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return render_template(
            "register.html",
            message="Registration Failed."
        )
    conn.close()
    return render_template("success.html")
# LOGIN PAGE (GET)
@app.route("/login")
def login():
    return render_template("login.html")
# LOGIN CHECK (POST)
@app.route("/login", methods=["POST"])
def login_check():
    email = request.form["email"]
    password = request.form["password"]
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # First check if email exists
    cursor.execute("""
        SELECT * FROM Candidate WHERE email=?
    """, (email,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return render_template("login.html",
                               message="Email ID is not registered.")
    #  If email exists, check password
    if user["password"] != password:
        conn.close()
        return render_template("login.html",
                               message="Incorrect Password.")
    # If both correct
    session.clear()
    session["candidate_id"] = user["candidate_id"]
    session["candidate_name"] = user["name"]
    conn.close()
    return redirect("/login_success")
#Login success page
@app.route("/login_success")
def login_success():
    if "candidate_name" not in session:
        return redirect("/login")
    return render_template("login_success.html",
        name=session["candidate_name"])
#Dashboard
@app.route("/dashboard")
def dashboard():
    if "candidate_id" not in session:
        return redirect("/login")
    candidate_id = session["candidate_id"]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name,email
        FROM Candidate
        WHERE candidate_id=?
    """, (candidate_id,))
    user = cursor.fetchone()
    cursor.execute("""
        SELECT status
        FROM Session
        WHERE candidate_id=?
        ORDER BY session_id DESC
        LIMIT 1
    """, (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] == "Paused":
        button_text = "Resume Exam"
    elif row and row[0] == "Ended":
        button_text = "start new exam"
    else:
        button_text = "Pause Exam"
    return render_template(
        "dashboard.html",
        exam_ended= False,
        candidate_id=candidate_id,
        name=user[0],
        email=user[1],
        button_text=button_text
    )
# logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
#Start Exam
@app.route("/start_exam")
def start_exam():
   
    import face_detection
    face_detection.monitoring = True
    face_detection.paused = False
    return {"status": "started"}  
#toggle exam
@app.route("/toggle_exam")
def toggle_exam():
    import face_detection
    face_detection.paused = not face_detection.paused
    return {"status": "paused" if face_detection.paused else "resumed"} 
# End Exam
@app.route("/end_exam")
def end_exam():
    if "candidate_id" not in session:
        return redirect("/login")
    import face_detection
    candidate_id = session["candidate_id"]
    candidate_name = session["candidate_name"]
    # Stop monitoring
    face_detection.monitoring = False
    face_detection.paused = False
    #  Connect to DB
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    # Count suspicious events
    cursor.execute("""
        SELECT COUNT(*) FROM EventLog
        WHERE candidate_id=? AND event_type='Face Not Detected'
    """, (candidate_id,))
    face_not_detected_count = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM EventLog
        WHERE candidate_id=? AND event_type='Browser Focus Lost'
    """, (candidate_id,))
    browser_focus_lost_count = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM EventLog
        WHERE candidate_id=? AND event_type='Multiple Faces Detected'
    """, (candidate_id,))
    multiple_face_count = cursor.fetchone()[0]
    conn.close()
    # Calculate score fresh every time
    integrity_score = 100
    integrity_score -= face_not_detected_count * 5
    integrity_score -= browser_focus_lost_count * 5
    integrity_score -= multiple_face_count * 5
    integrity_score = max(integrity_score, 0)
    if integrity_score >= 90:
        integrity_status = "Excellent Integrity"
    elif integrity_score >= 70:
        integrity_status = "Minor Violations"
    elif integrity_score >= 50:
        integrity_status = "Suspicious"
    else:
        integrity_status = "High Risk"
    #  Final face data
    final_face_status = face_detection.face_status
    final_absence_count = face_detection.absence_count
    return render_template(
        "dashboard.html",
        exam_ended=True,
        name=candidate_name,
        candidate_id=candidate_id,
        final_face_status=final_face_status,
        final_absence_count=final_absence_count,
        focus_loss_count=browser_focus_lost_count,
        integrity_score=integrity_score,
        integrity_status=integrity_status
    )
@app.route("/monitor_status")
def monitor_status():
    import face_detection
    return {
        "face_status": face_detection.face_status,
        "absence_duration": face_detection.absence_duration,
        "absence_count": face_detection.absence_count,
        "face_count": face_detection.face_count
    }
@app.route('/check_warning')
def check_warning():
    import face_detection
    return {
        "face_status": "Face Not Detected" if face_detection.face_currently_absent else "Face Detected",
        "absence_duration": int(face_detection.total_absence_duration),
        "absence_count": face_detection.absence_count,
        "multiple_faces": face_detection.multiple_face_detected
    }
@app.route("/integrity_report")
def integrity_report():
    if "candidate_id" not in session:
        return redirect("/login")
    candidate_id = session["candidate_id"]
    candidate_name = session["candidate_name"]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    #Get latest session
    cursor.execute("""
        SELECT session_id, start_time, end_time
        FROM Session
        WHERE candidate_id=?
        ORDER BY session_id DESC
        LIMIT 1
    """, (candidate_id,))
    session_row = cursor.fetchone()
    if not session_row:
        conn.close()
        return "No session found"
    session_id, start_time, end_time = session_row
    # Count suspicious events
    cursor.execute("""
        SELECT event_type, timestamp
        FROM EventLog
        WHERE candidate_id=?
        ORDER BY timestamp ASC
    """, (candidate_id,))
    events = cursor.fetchall()
    # Monitoring statistics
    cursor.execute("""
        SELECT COUNT(*) FROM EventLog
        WHERE candidate_id=? AND event_type='Face Not Detected'
    """, (candidate_id,))
    face_absence_count = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM EventLog
        WHERE candidate_id=? AND event_type='Browser Focus Lost'
    """, (candidate_id,))
    browser_focus_loss_count = cursor.fetchone()[0]
    total_suspicious_events = face_absence_count + browser_focus_loss_count
    #  Calculate Integrity Score
    integrity_score = 100
    integrity_score -= face_absence_count * 5
    integrity_score -= browser_focus_loss_count * 5
    if integrity_score < 0:
        integrity_score = 0
    if integrity_score >= 90:
        remark = "Excellent Integrity"
    elif integrity_score >= 70:
        remark = "Minor Violations"
    elif integrity_score >= 50:
        remark = "Suspicious"
    else:
        remark = "High Risk"
    conn.close()
    return render_template(
        "integrity_report.html",
        candidate_id=candidate_id,
        candidate_name=candidate_name,
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
        face_absence_count=face_absence_count,
        browser_focus_loss_count=browser_focus_loss_count,
        total_suspicious_events=total_suspicious_events,
        integrity_score=integrity_score,
        remark=remark,
        events=events
    )
#log browser event
@app.route('/log_browser_event', methods=['POST'])
def log_browser_event():
    if "candidate_id" not in session:
        return {"status": "error"}
    candidate_id = session["candidate_id"]
    data = request.get_json()
    event_type = data.get("event_type")
    remarks = data.get("remarks")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #  SQLite
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO EventLog(candidate_id, event_type, timestamp, remarks)
        VALUES (?, ?, ?, ?)
    """, (candidate_id, event_type, timestamp, remarks))
    #  Write to CSV
    import csv, os
    file_path = "eventlog.csv"
    if not os.path.exists(file_path):
        with open(file_path, "w", newline="") as f:
            csv.writer(f).writerow(
                ["Event ID", "Candidate ID", "Event Type", "Timestamp", "Remarks"]
            )
    with open(file_path, "r", newline="") as f:
        event_id = len(list(csv.reader(f)))
    with open(file_path, "a", newline="") as f:
        csv.writer(f).writerow(
            [event_id, candidate_id, event_type, timestamp, remarks]
        )
    print("Logged:", event_type)
    return {"status": "success"}
# Run Application
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)