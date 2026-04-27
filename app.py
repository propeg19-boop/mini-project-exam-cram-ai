# app.py — ExamCram AI: Main Flask Application
# ─────────────────────────────────────────────
# Entry point. All 3 routes are defined here.
# Each route delegates its logic to utils/.

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from utils.priority import build_study_plan
from utils.ai_handler import generate_answer
from utils.image_fetcher import fetch_images

# Load API keys from .env
load_dotenv()

app = Flask(__name__)


# ─────────────────────────────────────────────
# ROUTE 1: /generate-plan
# Accepts questions + study context.
# Returns a priority table and day-by-day plan.
# ─────────────────────────────────────────────
@app.route("/generate-plan", methods=["POST"])
def generate_plan():
    data = request.get_json()

    # Validate all required fields are present
    for field in ["questions", "days", "level", "tone"]:
        if field not in data:
            return jsonify({"error": f"Missing field: '{field}'"}), 400

    questions_raw = data["questions"]   # newline-separated string
    days          = int(data["days"])
    level         = data["level"]       # e.g. "beginner", "advanced"
    tone          = data["tone"]        # e.g. "formal", "casual"

    # Split raw string into individual question lines
    questions = [q.strip() for q in questions_raw.strip().split("\n") if q.strip()]

    if not questions:
        return jsonify({"error": "No questions found. Put each question on a new line."}), 400

    result = build_study_plan(questions, days, level, tone)
    return jsonify(result), 200


# ─────────────────────────────────────────────
# ROUTE 2: /generate-answer
# Sends a question to Gemini AI and returns
# a structured 4-section answer.
# ─────────────────────────────────────────────
@app.route("/generate-answer", methods=["POST"])
def answer():
    data = request.get_json()

    for field in ["question", "mode", "level", "tone"]:
        if field not in data:
            return jsonify({"error": f"Missing field: '{field}'"}), 400

    question = data["question"]
    mode     = data["mode"]    # "focused" or "quick"
    level    = data["level"]
    tone     = data["tone"]

    if mode not in ("focused", "quick"):
        return jsonify({"error": "Mode must be 'focused' or 'quick'"}), 400

    result = generate_answer(question, mode, level, tone)
    return jsonify(result), 200


# ─────────────────────────────────────────────
# ROUTE 3: /get-images
# Fetches diagram images from SerpAPI
# (Google Images) for a given topic.
# ─────────────────────────────────────────────
@app.route("/get-images", methods=["POST"])
def get_images():
    data = request.get_json()

    if "topic" not in data:
        return jsonify({"error": "Missing field: 'topic'"}), 400

    topic  = data["topic"]
    result = fetch_images(topic)
    return jsonify(result), 200


# ─────────────────────────────────────────────
# Start the server (debug=True for development)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
