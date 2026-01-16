import os
import smtplib
import json
import requests
import fitz  # PyMuPDF
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from bs4 import BeautifulSoup

from daily_job_matcher import match_jobs

# Load environment variables
load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "").strip()
EMAIL_USER = os.getenv("EMAIL_USER", "").strip()
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").replace(" ", "")

# Load config rules
with open("config.json") as f:
    CONFIG = json.load(f)

# File to store history of sent jobs
HISTORY_FILE = "job_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_history(history_set):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(history_set), f)

def extract_pdf_text(path):
    try:
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error reading resume: {e}")
        return ""

def fetch_jobs_from_apify():
    print("Fetching jobs from Apify...")
    url = f"https://api.apify.com/v2/acts/curious_coder~linkedin-jobs-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    
    # Configuration from config.json
    queries = CONFIG.get("job_queries", [])
    apify_settings = CONFIG.get("apify", {})
    
    payload = {
        "count": apify_settings.get("max_items", 100),
        "scrapeCompany": apify_settings.get("scrape_company", True),
        "urls": queries
    }
    
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 201 and response.status_code != 200:
        print(f"Apify Error: {response.text}")
        return []
    
    return response.json()

def normalize_job_data(apify_items):
    jobs = []
    for item in apify_items:
        # Get raw description (often HTML)
        raw_desc = item.get("description", "") or item.get("descriptionText", "")
        
        # Strip HTML to plain text
        if raw_desc:
            soup = BeautifulSoup(raw_desc, "html.parser")
            clean_desc = soup.get_text(separator=" ")
        else:
            clean_desc = ""

        # Clean URL to ensure better deduplication (remove query params)
        raw_url = item.get("jobUrl") or item.get("url") or item.get("link") or item.get("applyUrl") or "#"
        clean_url = raw_url.split("?")[0] if raw_url else "#"

        # Map Apify fields to our matcher expectations
        jobs.append({
            "title": item.get("title", ""),
            "company": item.get("companyName", ""),
            "description": clean_desc,
            "location": item.get("location", ""),
            "postedAt": item.get("postedAt", "Unknown"), 
            "url": clean_url
        })
    return jobs

def send_email(results):
    if not results:
        print("No matches found to email.")
        return

    # Determine how many jobs to send (default 10)
    limit = CONFIG.get("settings", {}).get("top_results_limit", 10)

    print(f"Sending email with top {min(len(results), limit)} jobs...")
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    msg['Subject'] = f"Your Daily Top {limit} Job Matches"

    # Build HTML body
    html_content = "<h2>🔥 Top matches for you today</h2><ul>"
    
    for job in results[:limit]:
        score = job.get("match_score", 0)
        color = "green" if score > 10 else "orange"
        html_content += f"""
        <li style="margin-bottom: 20px;">
            <strong style="font-size: 16px;">
                <a href="{job['url']}">{job['title']}</a> at {job['company']}
            </strong><br>
            <span style="color: {color}; font-weight: bold;">Score: {score}</span> | {job['location']}<br>
        </li>
        """
    html_content += "</ul>"
    
    msg.attach(MIMEText(html_content, 'html'))

    try:
        # Connect to Gmail SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, EMAIL_USER, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"\n[!] Email Failed: {e}")
        print("Login refused. Please check your EMAIL_USER and EMAIL_PASSWORD in .env.")
        print("Tip: Ensure you are using a Google App Password, not your normal password.")
        print("Skipping local save as per preference.")

def main():
    # 1. Read Resume
    settings = CONFIG.get("settings", {})
    resume_path = settings.get("resume_path", "Dan Yi Jia_Resume.pdf")
    
    if not os.path.exists(resume_path):
        print(f"Resume not found at {resume_path}")
        return
    
    resume_text = extract_pdf_text(resume_path)
    if not resume_text:
        return

    # 2. Fetch Jobs
    raw_jobs = fetch_jobs_from_apify()
    print(f"Fetched {len(raw_jobs)} raw jobs from Apify.")
    
    if not raw_jobs:
        print("No jobs fetched. Exiting.")
        return

    # 3. Optimize Data
    clean_jobs = normalize_job_data(raw_jobs)

    # 4. Match
    # Filter out jobs already in history
    history = load_history()
    new_jobs = [j for j in clean_jobs if j['url'] not in history]
    print(f"Filtered out {len(clean_jobs) - len(new_jobs)} previously seen jobs.")
    
    matches = match_jobs(resume_text, new_jobs)
    print(f"Ranked {len(matches)} jobs.")

    # 5. Email
    # Only send if we have matches and a password set
    if EMAIL_PASSWORD:
        if "App Password" not in EMAIL_PASSWORD:
             print("Warning: Email password might not be an App Password.")
        
        # Send email
        send_email(matches)
        
        # Update history with the jobs we just sent/processed
        # We track all matches that were qualified enough to be returned
        # Or should we only track the top N sent?
        # Let's track all valid matches so we don't re-process them tomorrow
        limit = settings.get("top_results_limit", 10)
        sent_jobs = matches[:limit]
        
        for job in sent_jobs:
            history.add(job['url'])
        
        save_history(history)
        print(f"Updated history with {len(sent_jobs)} new jobs.")
    else:
        print("Skipping email send. Please set EMAIL_PASSWORD in .env to send real emails.")

if __name__ == "__main__":
    main()
