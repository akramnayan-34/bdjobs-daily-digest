# What changed and why

## New files
- `jobdigest/state.py` — persistent `state.json`, dedupe, deadline-expiry check, pruning.
- `jobdigest/bdjobs_client.py` — job list fetch (now paginated/multi-category)
  + new full-description fetch (API attempt + HTML fallback).
- `jobdigest/profile_prompt.py` — your full profile, eligibility rules, and
  scoring rubric as plain data. Edit this file (not the logic files) when
  your CV changes.
- `jobdigest/eligibility_scoring.py` — sends jobs to Gemini in small
  batches, requires a structured JSON array back, validates it, and marks
  anything malformed/missing as `UNVERIFIED` rather than dropping it
  silently.
- `jobdigest/render.py` — builds the exact Telegram format you specified,
  from validated JSON only. Chunks on job boundaries, not raw characters.
- `jobdigest/telegram_client.py` — same send logic as before, plus
  retry/backoff.

## Changed
- `digest.py` — now an orchestrator that imports the modules above. Still
  the entry point (`python digest.py`), so your workflow's run command
  doesn't need to change.
- `requirements.txt` — added `beautifulsoup4` for the HTML fallback.

## MUST be verified against the live site (I have no network access to test this)
1. **`_fetch_details_via_api()`** in `bdjobs_client.py` uses an
   undocumented endpoint
   (`gateway.bdjobs.com/ActtivejobsTest/api/JobSubsystem/jobDetails`)
   found via third-party reverse-engineering, with guessed field names
   (`jobDescription`, `jobRequirement`, etc.). **Run it once manually and
   print the raw JSON** to confirm the real field names, then update
   `candidate_fields` in that function.
2. If the API approach fails, the HTML fallback
   (`_fetch_details_via_html`) strips all visible text from
   `jobdetails.asp?id=X` as a blunt fallback. It will work but is noisy —
   worth tightening to a specific container selector once you've seen a
   real page's HTML.
3. `deadline` extraction from the list API (`job.get("deadline")`) is a
   guess at the field name — check the raw list JSON and correct it in
   `digest.py` if needed.
4. `GEMINI_MODEL = "gemini-2.5-flash"` — confirm this model id is valid
   for your API key (your old code used `gemini-3.6-flash`, which may or
   may not be current — verify against Google's docs).

## Not yet done (waiting on you)
- **Workflow YAML update** — I don't have your current
  `.github/workflows/*.yml` content. It needs:
  - `permissions: contents: write`
  - A step after the script runs to `git add state.json && git commit && git push`
  Paste your current workflow file and I'll give you the exact diff.
- Step 6 from the plan (adding ReliefWeb as a second source) — not built
  yet, intentionally, since you said to do the core rebuild first.
