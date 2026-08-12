"""
Persistent state for the job digest, stored as a single JSON file that the
GitHub Actions workflow commits back to the repo after each run.

This is intentionally a flat JSON file (not a database) to match the
zero-infra, GitHub-Actions-only nature of this project.
"""

import json
import os
from datetime import datetime, timedelta, timezone

DEFAULT_STATE = {
    "last_run": None,
    "jobs": {}  # job_id -> {source, first_seen, last_sent, deadline,
                #            eligibility_status, total_score, url,
                #            duplicate_group}
}

# Don't re-send a job that was already sent in the shortlist within this
# many days, even if it still matches (avoids daily repeats of the same job).
RESEND_COOLDOWN_DAYS = 3

# Drop jobs from state entirely once they've been unseen (not returned by
# the collector) for this many days, to keep the file from growing forever.
PRUNE_AFTER_DAYS = 45


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return json.loads(json.dumps(DEFAULT_STATE))  # deep copy
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "jobs" not in data:
            data["jobs"] = {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARNING: could not read state file ({e}); starting fresh.")
        return json.loads(json.dumps(DEFAULT_STATE))


def save_state(path: str, state: dict) -> None:
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def was_recently_sent(job_id: str, state: dict) -> bool:
    entry = state["jobs"].get(job_id)
    if not entry or not entry.get("last_sent"):
        return False
    try:
        last_sent = datetime.fromisoformat(entry["last_sent"])
    except ValueError:
        return False
    return _now() - last_sent < timedelta(days=RESEND_COOLDOWN_DAYS)


def mark_seen(state: dict, job_id: str, source: str, url: str) -> None:
    entry = state["jobs"].setdefault(job_id, {})
    entry["source"] = source
    entry["url"] = url
    entry.setdefault("first_seen", _now().isoformat())
    entry["last_checked"] = _now().isoformat()


def mark_sent(state: dict, job_id: str, eligibility_status: str,
              total_score, deadline: str = None,
              duplicate_group: str = None) -> None:
    entry = state["jobs"].setdefault(job_id, {})
    entry["last_sent"] = _now().isoformat()
    entry["eligibility_status"] = eligibility_status
    entry["total_score"] = total_score
    if deadline:
        entry["deadline"] = deadline
    if duplicate_group:
        entry["duplicate_group"] = duplicate_group


def is_expired(deadline_str: str) -> bool:
    """Best-effort deadline check. Returns False (not expired) if the
    deadline can't be parsed, since we'd rather show an uncertain job than
    silently drop a valid one."""
    if not deadline_str:
        return False
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d-%b-%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(deadline_str.strip(), fmt).replace(
                tzinfo=timezone.utc)
            return dt.date() < _now().date()
        except ValueError:
            continue
    return False


def prune_stale(state: dict) -> None:
    cutoff = _now() - timedelta(days=PRUNE_AFTER_DAYS)
    stale_ids = []
    for job_id, entry in state["jobs"].items():
        last_checked = entry.get("last_checked") or entry.get("first_seen")
        if not last_checked:
            continue
        try:
            dt = datetime.fromisoformat(last_checked)
        except ValueError:
            continue
        if dt < cutoff:
            stale_ids.append(job_id)
    for job_id in stale_ids:
        del state["jobs"][job_id]
