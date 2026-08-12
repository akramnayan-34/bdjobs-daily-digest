import os
import requests

# ---------------- TARGET KEYWORDS & LOCATIONS ----------------
# Edit these keywords to match your exact preferred roles
TARGET_KEYWORDS = [
    "program officer",
    "project coordinator",
    "social work",
    "ngo",
    "monitoring",
    "evaluator",
    "project officer",
]

# Add specific locations (e.g., ["Sylhet", "Dhaka"]) or leave empty [] to match all
PREFERRED_LOCATIONS = []

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# -----------------------------------------------------------


def fetch_bdjobs():
    """Fetches the latest job postings from BDjobs Gateway."""
    url = "https://gateway.bdjobs.com/recruitment-account-test/api/JobSearch/GetJobSearch?isPro=1&rpp=50&pg=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("jobList", [])
    except Exception as e:
        print(f"Error fetching BDjobs: {e}")
        return []


def filter_jobs(job_list):
    """Filters jobs matching targeted keywords or locations."""
    shortlist = []

    for job in job_list:
        title = job.get("jobTitle", "")
        company = job.get("companyName", "")
        location = job.get("jobLocation", "")
        deadline = job.get("deadline", "N/A")
        job_id = job.get("jobId")

        combined_text = f"{title} {company}".lower()

        keyword_match = any(kw.lower() in combined_text for kw in TARGET_KEYWORDS)

        location_match = True
        if PREFERRED_LOCATIONS:
            location_match = any(
                loc.lower() in location.lower() for loc in PREFERRED_LOCATIONS
            )

        if keyword_match and location_match:
            job_url = f"https://jobs.bdjobs.com/jobdetails.asp?id={job_id}"
            shortlist.append(
                {
                    "title": title,
                    "company": company,
                    "location": location or "Not Specified",
                    "deadline": deadline,
                    "url": job_url,
                }
            )

    return shortlist


def send_telegram_digest(jobs):
    """Formats and dispatches the shortlist to Telegram."""
    if not jobs:
        message = "📌 *BDjobs Daily Digest*\nNo new matching positions found today."
    else:
        message = f"🎯 *BDjobs Daily Shortlist ({len(jobs)} Found)*\n\n"
        for i, job in enumerate(jobs[:10], 1):
            message += (
                f"*{i}. {job['title']}*\n"
                f"🏢 {job['company']}\n"
                f"📍 {job['location']} | ⏳ Deadline: {job['deadline']}\n"
                f"🔗 [View & Apply]({job['url']})\n\n"
            )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    res = requests.post(url, json=payload)
    if res.status_code == 200:
        print("Digest successfully sent to Telegram.")
    else:
        print(f"Failed to send Telegram message: {res.text}")


if __name__ == "__main__":
    jobs = fetch_bdjobs()
    shortlisted = filter_jobs(jobs)
    send_telegram_digest(shortlisted)
