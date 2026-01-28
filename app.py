import os
import json
from datetime import datetime, date, timedelta

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from models import init_db, SessionLocal, Activity
from ai_client import generate_text_from_prompt, generate_from_pdf, extract_text_from_pdf, call_ollama

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()


def log_activity(kind: str, title: str, details: str = ""):
    session = SessionLocal()
    try:
        activity = Activity(
            kind=kind,
            title=title[:200],
            details=details[:2000],
            created_at=datetime.utcnow(),
        )
        session.add(activity)
        session.commit()
    finally:
        session.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():
    session = SessionLocal()
    try:
        total_notes = session.query(Activity).filter_by(kind="notes").count()
        total_quiz = session.query(Activity).filter_by(kind="quiz").count()

        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())

        today_actions = (
            session.query(Activity)
            .filter(Activity.created_at >= today_start, Activity.created_at <= today_end)
            .count()
        )

        streak = 0
        day_offset = 0
        while True:
            day_start = datetime.combine(date.today() - timedelta(days=day_offset), datetime.min.time())
            day_end = datetime.combine(date.today() - timedelta(days=day_offset), datetime.max.time())
            count = (
                session.query(Activity)
                .filter(Activity.created_at >= day_start, Activity.created_at <= day_end)
                .count()
            )
            if count == 0:
                break
            streak += 1
            day_offset += 1

        daily_goal = 4
        progress = min(100, int(today_actions / daily_goal * 100)) if daily_goal else 0

        return jsonify(
            {
                "notesCreated": total_notes,
                "quizzesTaken": total_quiz,
                "dayStreak": streak,
                "todayActions": today_actions,
                "dailyGoal": daily_goal,
                "goalProgress": progress,
            }
        )
    finally:
        session.close()


@app.route("/api/history")
def history():
    session = SessionLocal()
    try:
        items = (
            session.query(Activity)
            .order_by(Activity.created_at.desc())
            .limit(30)
            .all()
        )
        data = [
            {
                "kind": a.kind,
                "title": a.title,
                "details": a.details,
                "createdAt": a.created_at.isoformat() + "Z",
            }
            for a in items
        ]
        return jsonify({"items": data})
    finally:
        session.close()


@app.route("/api/notes", methods=["POST"])
def api_notes():
    pdf = request.files.get("file")
    prompt = request.form.get("prompt", "").strip()

    if not pdf:
        return jsonify({"error": "PDF file is required"}), 400

    filename = secure_filename(pdf.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    pdf.save(path)

    extra_instruction = prompt or "Create clear, well-structured study notes with headings and bullet points."
    text = generate_from_pdf(path, extra_instruction)

    log_activity("notes", f"Notes from {filename}", extra_instruction)
    return jsonify({"notes": text})


@app.route("/api/quiz", methods=["POST"])
def api_quiz():
    pdf = request.files.get("file")
    num_questions = request.form.get("numQuestions", "").strip()
    if not num_questions.isdigit():
        num_questions = "5"

    if not pdf:
        return jsonify({"error": "PDF file is required"}), 400

    filename = secure_filename(pdf.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    pdf.save(path)

    pdf_text = extract_text_from_pdf(path, max_pages=5)

    prompt = f"""You are an exam question generator.

From the study material below, create {num_questions} multiple-choice questions.

IMPORTANT RULES:
- Return ONLY valid JSON. No explanation before or after.
- JSON format MUST be:

{{
  "questions": [
    {{
      "question": "question text",
      "options": ["option A", "option B", "option C", "option D"],
      "answer_index": 0
    }}
  ]
}}

Where "answer_index" is 0,1,2, or 3 (index into the options array).

Study material:
{pdf_text}
"""

    raw = call_ollama(prompt)

    try:
        data = json.loads(raw)
        questions = data.get("questions", [])
    except Exception:
        return jsonify({"error": "AI did not return valid quiz JSON. Please try again with fewer questions or a smaller PDF.

Raw output (first 400 chars):
" + raw[:400]}), 500

    log_activity("quiz", f"Quiz ({num_questions} Qs) from {filename}", "")
    return jsonify({"questions": questions})


@app.route("/api/questions", methods=["POST"])
def api_questions():
    pdf = request.files.get("file")
    prompt = request.form.get("prompt", "").strip()

    if not pdf:
        return jsonify({"error": "PDF file is required"}), 400

    filename = secure_filename(pdf.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    pdf.save(path)

    extra_instruction = prompt or "Create exam-style descriptive questions from this PDF."
    questions = generate_from_pdf(path, extra_instruction)

    log_activity("questions", f"Questions from {filename}", extra_instruction)
    return jsonify({"questions": questions})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question is required"}), 400

    prompt = "You are a helpful tutor. Answer the student's question clearly.

Question: " + question
    answer = generate_text_from_prompt(prompt)

    log_activity("chat", "AI Chat question", question)
    return jsonify({"answer": answer})


@app.route("/api/mentor", methods=["POST"])
def api_mentor():
    data = request.get_json(force=True)
    subject = data.get("subject", "").strip()
    total_days = data.get("totalDays", "").strip()
    hours_per_day = data.get("hoursPerDay", "").strip()
    level = data.get("level", "").strip() or "beginner / intermediate"
    notes = data.get("notes", "").strip()

    if not subject or not total_days or not hours_per_day:
        return jsonify({"error": "Please fill subject, total days, and hours per day."}), 400

    prompt = f"""You are an expert study planner.

Create a day-by-day study plan.

Subject / Topic: {subject}
Total days to finish: {total_days}
Hours per day: {hours_per_day}
Level: {level}
Extra notes: {notes}

Give the plan in a clear table-style text with Day number, Topics, and Tasks."""

    plan = generate_text_from_prompt(prompt)
    log_activity("mentor", f"Study plan for {subject}", f"{total_days} days, {hours_per_day} h/day")

    return jsonify({"plan": plan})


if __name__ == "__main__":
    app.run(debug=True)
