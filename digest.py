"""
Entry point -- kept named digest.py so the existing GitHub Action workflow
(`python digest.py`) does not need to change its run command.
"""

import os

from jobdigest import state as state_mod
from jobdigest.bdjobs_client import fetch_bdjobs_list, fetch_job_details
from jobdigest.eligibility_scoring import score_jobs
from jobdigest.render import build_digest_text, chunk_message
from jobdigest.telegram_client import send_telegram_digest

STATE_PATH = os.getenv("STATE_PATH", "state.json")

NGO_KEYWORDS = [
    "ngo", "development",
]

# Cap on how many jobs we fetch full descriptions + send to the LLM for,
# per run -- protects against runaway API usage if a category is large.
MAX_JOBS_PER_RUN = 40


def keyword_prefilter(raw_jobs: list) -> list:
    kept = []
    for job in raw_jobs:
        title = job.get("jobTitle", "")
        company = job.get("companyName", "")
        combined = f"{title} {company}".lower()
        if any(kw in combined for kw in NGO_KEYWORDS):
            kept.append(job)
    return kept


def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not gemini_key:
        print("ERROR: GEMINI_API_KEY not set. Aborting.")
        return

    state = state_mod.load_state(STATE_PATH)

    print("Fetching job list...")
    raw_jobs = fetch_bdjobs_list()
    prefiltered = keyword_prefilter(raw_jobs)
    print(f"{len(prefiltered)} jobs passed keyword pre-filter "
          f"(of {len(raw_jobs)} fetched).")

    candidates = []
    for job in prefiltered:
        job_id = str(job.get("jobId"))
        if not job_id or job_id == "None":
            continue
        if state_mod.was_recently_sent(job_id, state):
            continue
        candidates.append(job)

    candidates = candidates[:MAX_JOBS_PER_RUN]
    print(f"{len(candidates)} candidate jobs after dedupe/cap, fetching "
          f"full descriptions...")

    jobs_for_scoring = []
    for job in candidates:
        job_id = str(job.get("jobId"))
        url = f"https://jobs.bdjobs.com/jobdetails.asp?id={job_id}"
        description_text = fetch_job_details(job_id)
        if not description_text:
            print(f"WARNING: could not retrieve full description for "
                  f"job {job_id}; will be marked UNVERIFIED unless "
                  f"obviously ineligible.")
        jobs_for_scoring.append({
            "job_id": job_id,
            "title": job.get("jobTitle", "N/A"),
            "company": job.get("companyName", "N/A"),
            "location": job.get("jobLocation", "N/A"),
            "experience": job.get("experience", "N/A"),
            "deadline": job.get("deadline") or job.get("applicationDeadline"),
            "url": url,
            "description_text": description_text,
        })
        state_mod.mark_seen(state, job_id, "bdjobs", url)

    if not jobs_for_scoring:
        print("No new candidate jobs today.")
        text = build_digest_text([])
        send_telegram_digest(chunk_message(text), bot_token, chat_id)
        state_mod.prune_stale(state)
        state_mod.save_state(STATE_PATH, state)
        return

    print(f"Scoring {len(jobs_for_scoring)} jobs via LLM...")
    results = score_jobs(jobs_for_scoring, gemini_key)

    for r in results:
        meta = r["_job_meta"]
        deadline = meta.get("deadline")
        if deadline and state_mod.is_expired(deadline):
            r["eligibility_status"] = "INELIGIBLE"
            r.setdefault("eligibility_reasons", []).append(
                "Deadline has passed.")

    text = build_digest_text(results)
    chunks = chunk_message(text)

    print("Dispatching to Telegram...")
    send_telegram_digest(chunks, bot_token, chat_id)

    for r in results:
        meta = r["_job_meta"]
        state_mod.mark_sent(
            state, meta["job_id"], r["eligibility_status"],
            r.get("total_score"), meta.get("deadline"),
            r.get("duplicate_group"),
        )

    state_mod.prune_stale(state)
    state_mod.save_state(STATE_PATH, state)
    print("Done.")


if __name__ == "__main__":
    main()
