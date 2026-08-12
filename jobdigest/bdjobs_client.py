"""
BDJobs collection: job list + full job description.

IMPORTANT: fetch_job_details() uses an undocumented/reverse-engineered API
endpoint plus an HTML fallback. Both must be verified against the live site
-- they were not tested against a live network connection when written.
Check the logs after the first real run and adjust SELECTORS/endpoints if
BDJobs' site structure differs.
"""

import re
import requests

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

LIST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://jobs.bdjobs.com/",
    "Origin": "https://jobs.bdjobs.com",
}

# Category IDs to pull. 12 was the original single category; add/adjust
# after confirming what each fcatId maps to on bdjobs.com. Kept as a list so
# it's a one-line change to widen coverage.
CATEGORY_IDS = [12]
RESULTS_PER_PAGE = 50
MAX_PAGES_PER_CATEGORY = 3  # raise if a category regularly has >150 results


def fetch_bdjobs_list() -> list:
    """Fetch job list metadata across configured categories/pages.
    Returns a de-duplicated list of raw job dicts as returned by the API."""
    all_jobs = []
    seen_ids = set()

    for cat_id in CATEGORY_IDS:
        for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
            url = (
                "https://gateway.bdjobs.com/recruitment-account-test/api/"
                f"JobSearch/GetJobSearch?isPro=1&rpp={RESULTS_PER_PAGE}"
                f"&pg={page}&fcatId={cat_id}"
            )
            try:
                response = requests.get(url, headers=LIST_HEADERS, timeout=20)
                if response.status_code != 200:
                    print(f"BDJobs list blocked/failed (cat={cat_id} "
                          f"page={page}): status {response.status_code}")
                    break
                data = response.json()
            except Exception as e:
                print(f"Error fetching BDJobs list (cat={cat_id} "
                      f"page={page}): {e}")
                break

            page_jobs = _extract_job_list(data)
            if not page_jobs:
                break  # no more pages

            new_count = 0
            for job in page_jobs:
                job_id = job.get("jobId")
                if job_id and job_id not in seen_ids:
                    seen_ids.add(job_id)
                    all_jobs.append(job)
                    new_count += 1

            if new_count < RESULTS_PER_PAGE:
                break  # last page for this category

    print(f"Fetched {len(all_jobs)} unique jobs from BDJobs "
          f"across {len(CATEGORY_IDS)} categor(y/ies).")
    return all_jobs


def _extract_job_list(data) -> list:
    """Bulletproof extraction: handle whatever structure the API returns."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        inner = data.get("data", data)
        if isinstance(inner, list):
            return inner
        if isinstance(inner, dict):
            return inner.get("jobList", [])
    return []


def fetch_job_details(job_id) -> str:
    """Return the full job description/requirements text for a job, or an
    empty string if it could not be retrieved. Callers MUST treat an empty
    result as 'could not verify' -- never as 'no restrictions found'."""
    text = _fetch_details_via_api(job_id)
    if text:
        return text
    return _fetch_details_via_html(job_id)


def _fetch_details_via_api(job_id) -> str:
    url = (
        "https://gateway.bdjobs.com/ActtivejobsTest/api/JobSubsystem/"
        f"jobDetails?jobId={job_id}"
    )
    try:
        response = requests.get(url, headers=LIST_HEADERS, timeout=20)
        if response.status_code != 200:
            return ""
        data = response.json()
    except Exception as e:
        print(f"Details API failed for job {job_id}: {e}")
        return ""

    inner = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(inner, dict):
        return ""

    # Field names are unconfirmed -- try the most likely candidates and
    # concatenate whatever is present.
    candidate_fields = [
        "jobDescription", "jobResponsibilities", "jobRequirement",
        "additionalRequirement", "educationRequirement",
        "experienceRequirement", "compensation", "otherBenefit",
    ]
    parts = []
    for field in candidate_fields:
        val = inner.get(field)
        if val and isinstance(val, str):
            parts.append(val)
    return "\n".join(parts).strip()


def _fetch_details_via_html(job_id) -> str:
    url = f"https://jobs.bdjobs.com/jobdetails.asp?id={job_id}"
    try:
        response = requests.get(url, headers=LIST_HEADERS, timeout=20)
        if response.status_code != 200:
            return ""
        html = response.text
    except Exception as e:
        print(f"HTML fallback failed for job {job_id}: {e}")
        return ""

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        # Strip scripts/styles, then take visible text. This is a blunt
        # fallback -- verify against the live page and tighten the
        # selector (e.g. a specific container div/class) once known.
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text("\n")
        text = re.sub(r"\n{2,}", "\n", text).strip()
        return text[:6000]  # cap length to keep prompts manageable
    except ImportError:
        print("bs4 not installed; cannot run HTML fallback. "
              "Add beautifulsoup4 to requirements.txt.")
        return ""
