# utils/priority.py — Study Plan Builder
# ─────────────────────────────────────────────
# Classifies each question into High / Medium / Low priority
# by scanning for action verbs, then distributes questions
# across the available study days.
# No API calls — pure Python logic.

import math


# ─────────────────────────────────────────────
# ACTION VERB → PRIORITY MAP
# Based on Bloom's Taxonomy (knowledge level)
# ─────────────────────────────────────────────

HIGH_KEYWORDS   = ["define", "list", "state", "name", "what is", "what are", "identify"]
MEDIUM_KEYWORDS = ["explain", "describe", "write", "outline", "summarise",
                   "summarize", "illustrate", "discuss"]
LOW_KEYWORDS    = ["analyze", "analyse", "compare", "derive", "evaluate",
                   "differentiate", "contrast", "critically", "justify", "assess"]

# Human-readable time ranges shown to the student
TIME_RANGES = {
    "High":   "10–15 mins",
    "Medium": "20–30 mins",
    "Low":    "40–60 mins",
}


def get_priority(question: str) -> str:
    """
    Scan the question text for action verbs and return
    "High", "Medium", or "Low".
    Defaults to "Medium" if no keyword matches.
    """
    q = question.lower()

    for kw in HIGH_KEYWORDS:
        if kw in q:
            return "High"

    for kw in MEDIUM_KEYWORDS:
        if kw in q:
            return "Medium"

    for kw in LOW_KEYWORDS:
        if kw in q:
            return "Low"

    return "Medium"   # safe default


def build_table(questions: list) -> list:
    """
    Build a flat list of dicts — one per question.
    Sorted High → Medium → Low so quick wins come first.

    Each entry:
        { question, priority, estimated_time }
    """
    order = {"High": 0, "Medium": 1, "Low": 2}
    table = []

    for q in questions:
        priority = get_priority(q)
        table.append({
            "question":       q,
            "priority":       priority,
            "estimated_time": TIME_RANGES[priority],
        })

    table.sort(key=lambda row: order[row["priority"]])
    return table


def distribute_days(table: list, days: int) -> dict:
    """
    Chunk the sorted table into `days` groups.
    Returns: { "Day 1": [q1, q2], "Day 2": [q3], ... }
    """
    total   = len(table)
    per_day = math.ceil(total / days)
    day_plan = {}

    for day_num in range(1, days + 1):
        start  = (day_num - 1) * per_day
        chunk  = table[start : start + per_day]
        if chunk:
            day_plan[f"Day {day_num}"] = [row["question"] for row in chunk]

    return day_plan


def build_study_plan(questions: list, days: int, level: str, tone: str) -> dict:
    """
    Main function called by app.py.
    Returns the full study plan dict.
    """
    table    = build_table(questions)
    day_plan = distribute_days(table, days)

    return {
        "table":    table,
        "day_plan": day_plan,
        "meta": {
            "total_questions": len(questions),
            "days":            days,
            "level":           level,
            "tone":            tone,
        },
    }
