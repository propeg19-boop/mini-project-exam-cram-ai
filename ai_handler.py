# utils/ai_handler.py — Google Gemini Answer Generator
# ─────────────────────────────────────────────────────
# Calls the Gemini REST API to generate structured answers.
#
# FALLBACK ORDER (tries each model in sequence):
#   1. gemini-2.0-flash-lite   ← fastest, cheapest
#   2. gemma-3-27b-it          ← open model fallback
#   3. gemini-1.5-flash        ← reliable fallback
#   4. gemini-1.5-flash-8b     ← last resort
#
# The answer is returned as strict JSON with 4 keys:
#   analogy, understanding, answer, extra

import os
import re
import json
import requests


# ─────────────────────────────────────────────
# GEMINI REST ENDPOINT
# Format: .../models/{model}:generateContent
# ─────────────────────────────────────────────
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Models tried in order — if one fails, the next is used
FALLBACK_MODELS = [
    "gemini-2.0-flash-lite",
    "gemma-3-27b-it",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

# Returned when every model fails — keeps the frontend alive
FALLBACK_RESPONSE = {
    "analogy":       "Could not generate analogy at this time.",
    "understanding": "Could not generate understanding at this time.",
    "answer":        "The AI service is temporarily unavailable. Please try again shortly.",
    "extra":         "Tip: Try rephrasing your question or check your API key.",
}


# ─────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────

def build_prompt(question: str, mode: str, level: str, tone: str) -> str:
    """
    Build the prompt for Gemini.
    We instruct the model to return ONLY valid JSON — no markdown,
    no extra text — so we can reliably parse the response.
    """

    json_schema = """{
  "analogy": "A simple real-world analogy",
  "understanding": "Core idea in 1-2 sentences",
  "answer": "The complete answer",
  "extra": "One exam tip or common mistake"
}"""

    if mode == "focused":
        detail_instruction = (
            "Write a detailed, well-structured answer with full explanation. "
            "The 'answer' field should cover all key points thoroughly."
        )
    else:  # quick
        detail_instruction = (
            "Write a concise answer using short bullet points. "
            "The 'answer' field should be 3-5 bullets only — ideal for last-minute revision."
        )

    return f"""You are an expert teacher helping a {level} student prepare for an exam.
Tone: {tone}.
{detail_instruction}

IMPORTANT: You MUST respond with ONLY a valid JSON object. No markdown, no code blocks, no extra text.

Return exactly this JSON structure:
{json_schema}

Question: {question}"""


# ─────────────────────────────────────────────
# SINGLE MODEL CALLER
# ─────────────────────────────────────────────

def call_gemini(model: str, prompt: str, api_key: str) -> str:
    """
    Call one specific Gemini model and return the raw text response.
    Raises an exception if the call fails (caller handles fallback).
    """
    url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.4,      # Lower = more consistent/factual
            "maxOutputTokens": 1024,
        }
    }

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()

    # Navigate Gemini's response structure to get the text
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ─────────────────────────────────────────────
# RESPONSE PARSER
# ─────────────────────────────────────────────

def parse_json_response(raw_text: str) -> dict:
    """
    Parse the AI response into a Python dict.
    Handles cases where the model wraps output in ```json ... ``` fences.
    Returns FALLBACK_RESPONSE if parsing fails.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw_text).strip().rstrip("`").strip()

    try:
        parsed = json.loads(cleaned)

        # Ensure all 4 required keys exist; fill missing ones with empty string
        return {
            "analogy":       parsed.get("analogy", ""),
            "understanding": parsed.get("understanding", ""),
            "answer":        parsed.get("answer", ""),
            "extra":         parsed.get("extra", ""),
        }

    except json.JSONDecodeError:
        # JSON parse failed — return a safe fallback so the app never crashes
        return {**FALLBACK_RESPONSE, "extra": f"Parse error. Raw response: {raw_text[:200]}"}


# ─────────────────────────────────────────────
# MAIN ENTRY POINT (with automatic fallback)
# ─────────────────────────────────────────────

def generate_answer(question: str, mode: str, level: str, tone: str) -> dict:
    """
    Try each Gemini model in FALLBACK_MODELS order.
    Returns the first successful structured response.
    If ALL models fail, returns FALLBACK_RESPONSE.

    Called by app.py → /generate-answer route.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {**FALLBACK_RESPONSE, "extra": "Error: GEMINI_API_KEY is not set in your .env file."}

    prompt = build_prompt(question, mode, level, tone)
    last_error = ""

    for model in FALLBACK_MODELS:
        try:
            print(f"[AI] Trying model: {model}")
            raw_text = call_gemini(model, prompt, api_key)
            result   = parse_json_response(raw_text)
            print(f"[AI] Success with model: {model}")
            return result

        except requests.exceptions.Timeout:
            last_error = f"{model}: request timed out"
            print(f"[AI] Timeout on {model}, trying next...")

        except requests.exceptions.HTTPError as e:
            last_error = f"{model}: HTTP {e.response.status_code}"
            print(f"[AI] HTTP error on {model} ({e.response.status_code}), trying next...")

        except requests.exceptions.RequestException as e:
            last_error = f"{model}: {str(e)}"
            print(f"[AI] Request error on {model}, trying next...")

        except (KeyError, IndexError) as e:
            last_error = f"{model}: unexpected response structure — {str(e)}"
            print(f"[AI] Parse error on {model}, trying next...")

    # All models exhausted
    print(f"[AI] All models failed. Last error: {last_error}")
    return {**FALLBACK_RESPONSE, "extra": f"All AI models failed. Last error: {last_error}"}
