import os
import json
import requests

# ==================== CONFIGURATION ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Paste your entire prompt here (I have condensed it for the template, 
# but you should paste your FULL candidate profile and rules between the quotes)
RECRUITER_PROMPT = """
You are my PERSONAL CAREER RECRUITER. Your objective is to identify only the positions Md Akram Hussain (MSS in Social Work, 4+ years NGO experience) should seriously consider applying for.

Here is my profile summary:
- Expertise: Programme Management, Child Protection, MEAL, Social Work.
- Nationality: Bangladeshi
- Location: Sylhet, Bangladesh

CRITICAL ELIGIBILITY:
- Reject female-only jobs.
- Reject jobs requiring strict specialized experience I don't have.
- Reject jobs that don't match my career level.

OUTPUT FORMAT:
Generate a personalized Daily Telegram Output using the EXACT format provided in my instructions:
🔥 DAILY PERSONALIZED JOB SHORTLIST
[DATE]

🥇 PRIORITY 1
[Organization] - [Job Title]
📍 Location: ... 
(etc. including WHY YOU, MAIN GAP, VERDICT, Application Link)

EXCLUDED JOBS
(List up to 3 notable jobs excluded and the specific reason).

Evaluate the following jobs and return ONLY the final Markdown output:
"""
# =======================================================


def fetch_bdjobs():
    """Fetches the latest job listings with robust parsing for different API structures."""
    url = "https://gateway.bdjobs.com/recruitment-account-test/api/JobSearch/GetJobSearch?isPro=1&rpp=50&pg=1&fcatId=12"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://jobs.bdjobs.com/",
        "Origin": "https://jobs.bdjobs.com"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"Blocked by BDjobs! Status Code: {response.status_code}")
            return []
            
        data = response.json()
        jobs = []
        
        # Bulletproof extraction: Handle whatever structure the API throws at us
        if isinstance(data, list):
            # Scenario A: API returns the list directly
            jobs = data
        elif isinstance(data, dict):
            # Scenario B: API nests it inside 'data' or 'jobList'
            inner_data = data.get("data", data)
            if isinstance(inner_data, list):
                jobs = inner_data
            elif isinstance(inner_data, dict):
                jobs = inner_data.get("jobList", [])
                
        print(f"Successfully fetched {len(jobs)} jobs from BDjobs API.")
        return jobs
        
    except Exception as e:
        print(f"Error fetching BDjobs: {e}")
        return []


def analyze_with_ai(jobs):
    """Pre-filters for NGO keywords, then sends to Gemini AI."""
    if not jobs:
        return "No jobs fetched today."

    job_text_block = ""
    
    # 1. THE FAILSAFE PRE-FILTER
    # Only keep jobs that have these core words in the title or company name
    ngo_keywords = [
        "ngo", "development", "program", "project", "social", 
        "monitoring", "meal", "officer", "coordinator", "protection", 
        "research", "safeguarding", "humanitarian", "foundation"
    ]
    
    valid_jobs = 0
    for job in jobs:
        title = job.get("jobTitle", "N/A")
        company = job.get("companyName", "N/A")
        location = job.get("jobLocation", "N/A")
        exp = job.get("experience", "N/A")
        job_id = job.get("jobId")
        
        # Combine title and company name to check against our keywords
        combined_text = f"{title} {company}".lower()
        
        # If the job doesn't contain at least one of our NGO keywords, skip it entirely
        if not any(kw in combined_text for kw in ngo_keywords):
            continue 
            
        job_url = f"https://jobs.bdjobs.com/jobdetails.asp?id={job_id}"
        job_text_block += f"Title: {title}\nCompany: {company}\nLocation: {location}\nExperience: {exp}\nURL: {job_url}\n---\n"
        valid_jobs += 1

    if valid_jobs == 0:
        return "No matching NGO/Development jobs found in today's batch."

    # 2. SEND TO AI
    full_prompt = RECRUITER_PROMPT + "\n\nTODAY'S JOBS TO EVALUATE:\n" + job_text_block

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.2} 
    }

    try:
        res = requests.post(gemini_url, json=payload, headers={"Content-Type": "application/json"})
        res.raise_for_status()
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"AI Evaluation Failed: {e}")
        return f"AI Evaluation Failed. Pre-filtered jobs sent to AI: {valid_jobs}"


def send_telegram_digest(ai_markdown_text):
    """Sends the AI-curated Markdown response to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Telegram max message length is 4096. If the AI writes a very long analysis, split it.
    chunks = [ai_markdown_text[i:i+4000] for i in range(0, len(ai_markdown_text), 4000)]
    
    for chunk in chunks:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "Markdown", # Parses the AI's bolding and links natively
            "disable_web_page_preview": True,
        }
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"Failed to send chunk: {res.text}")
        else:
            print("Digest chunk sent successfully.")


if __name__ == "__main__":
    print("Fetching jobs...")
    raw_jobs = fetch_bdjobs()
    
    print("Analyzing jobs with Gemini AI...")
    ai_shortlist = analyze_with_ai(raw_jobs)
    
    print("Dispatching to Telegram...")
    send_telegram_digest(ai_shortlist)
