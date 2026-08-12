"""
Sends jobs (with full description text where available) to the LLM and
gets back structured JSON -- eligibility + score -- instead of free-form
Markdown. The calling code (render.py) builds the final Telegram message
from this validated data, so the model never freehand-writes the output.
"""

import json
import re
import requests

from .profile_prompt import CANDIDATE_PROFILE, ELIGIBILITY_RULES, SCORING_RUBRIC

GEMINI_MODEL = "gemini-2.5-flash"  # confirm this is a valid/current model id
                                    # for your account before relying on it
BATCH_SIZE = 8  # jobs per LLM call, keeps prompts short and responses reliable

REQUIRED_FIELDS = {
    "job_id", "eligibility_status", "eligibility_reasons", "scores",
    "total_score", "shortlist_probability", "career_value", "gaps",
    "verdict",
}
VALID_ELIGIBILITY = {"ELIGIBLE", "INELIGIBLE", "UNVERIFIED"}


def score_jobs(jobs: list, api_key: str) -> list:
    """jobs: list of dicts with at least job_id, title, company, location,
    url, description_text (may be empty string if unretrievable).
    Returns list of validated result dicts, one per input job (results for
    jobs that failed to parse are marked UNVERIFIED with a parse-error note
    rather than being silently dropped)."""
    results = []
    for i in range(0, len(jobs), BATCH_SIZE):
        batch = jobs[i:i + BATCH_SIZE]
        prompt = _build_prompt(batch)
        raw = _call_gemini(prompt, api_key)
        parsed = _parse_and_validate(raw, batch)
        results.extend(parsed)
    return results


def _build_prompt(batch: list) -> str:
    jobs_block = ""
    for job in batch:
        has_full_desc = bool(job.get("description_text"))
        jobs_block += (
            f"\n---\njob_id: {job['job_id']}\n"
            f"Title: {job.get('title', 'N/A')}\n"
            f"Company: {job.get('company', 'N/A')}\n"
            f"Location: {job.get('location', 'N/A')}\n"
            f"Listed experience requirement: {job.get('experience', 'N/A')}\n"
            f"Deadline (if known): {job.get('deadline', 'UNKNOWN')}\n"
            f"Full description retrieved: {'YES' if has_full_desc else 'NO'}\n"
            f"Description/requirements text:\n"
            f"{job.get('description_text') or '[NOT AVAILABLE -- treat as UNVERIFIED unless obviously ineligible from title/company alone]'}\n"
        )

    return f"""You are a personal recruitment analyst for the candidate described below.
Evaluate EACH job independently and return ONLY a JSON array (no prose, no
Markdown fences) with one object per job_id, using EXACTLY this schema:

[
  {{
    "job_id": "<same id as input>",
    "eligibility_status": "ELIGIBLE" | "INELIGIBLE" | "UNVERIFIED",
    "eligibility_reasons": ["short reason", ...],
    "scores": {{"technical": 0, "experience": 0, "mandatory": 0, "education": 0, "sector": 0, "career": 0}},
    "total_score": 0,
    "shortlist_probability": "High" | "Medium" | "Low" | null,
    "career_value": "High" | "Medium" | "Low" | null,
    "gaps": ["short gap", ...],
    "verdict": "APPLY FIRST" | "CONSIDER" | "SKIP" | "EXCLUDED",
    "duplicate_group": "<org+project+location label>" | null
  }}
]

Rules for "scores"/"total_score": only fill these in for ELIGIBLE jobs; use
null for all score fields when eligibility_status is INELIGIBLE or
UNVERIFIED.

CANDIDATE PROFILE:
{CANDIDATE_PROFILE}

{ELIGIBILITY_RULES}

{SCORING_RUBRIC}

JOBS TO EVALUATE:
{jobs_block}
"""


def _call_gemini(prompt: str, api_key: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1},
    }
    for attempt in range(3):
        try:
            res = requests.post(url, json=payload,
                                 headers={"Content-Type": "application/json"},
                                 timeout=60)
            res.raise_for_status()
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Gemini call failed (attempt {attempt + 1}/3): {e}")
    return ""


def _parse_and_validate(raw_text: str, batch: list) -> list:
    fallback = [_unverified_fallback(job, "LLM call failed or returned "
                                          "no parseable response")
                for job in batch]
    if not raw_text:
        return fallback

    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(),
                      flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"JSON parse failed: {e}")
        return fallback

    if not isinstance(parsed, list):
        print("LLM response was not a JSON array as required.")
        return fallback

    by_id = {job["job_id"]: job for job in batch}
    validated = []
    seen_ids = set()

    for item in parsed:
        if not isinstance(item, dict) or "job_id" not in item:
            continue
        job_id = item["job_id"]
        if job_id not in by_id:
            continue
        if not REQUIRED_FIELDS.issubset(item.keys()):
            missing = REQUIRED_FIELDS - item.keys()
            print(f"Job {job_id} missing fields {missing}; marking UNVERIFIED.")
            validated.append(_unverified_fallback(
                by_id[job_id], f"LLM response missing fields: {missing}"))
            seen_ids.add(job_id)
            continue
        if item["eligibility_status"] not in VALID_ELIGIBILITY:
            item["eligibility_status"] = "UNVERIFIED"
            item.setdefault("eligibility_reasons", []).append(
                "Invalid eligibility_status value from LLM; treated as unverified.")
        item["_job_meta"] = by_id[job_id]
        validated.append(item)
        seen_ids.add(job_id)

    # Any job the model dropped entirely still needs a result.
    for job in batch:
        if job["job_id"] not in seen_ids:
            validated.append(_unverified_fallback(
                job, "LLM did not return a result for this job."))

    return validated


def _unverified_fallback(job: dict, reason: str) -> dict:
    return {
        "job_id": job["job_id"],
        "eligibility_status": "UNVERIFIED",
        "eligibility_reasons": [reason],
        "scores": {k: None for k in
                   ("technical", "experience", "mandatory", "education",
                    "sector", "career")},
        "total_score": None,
        "shortlist_probability": None,
        "career_value": None,
        "gaps": [],
        "verdict": "EXCLUDED",
        "duplicate_group": None,
        "_job_meta": job,
    }

