import os
import smtplib
import json
import requests
import fitz  # PyMuPDF
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

from daily_job_matcher import match_jobs

# Load environment variables
load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "").strip()
EMAIL_USER = os.getenv("EMAIL_USER", "").strip()
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").replace(" ", "")

# Load config rules
with open("config.json") as f:
    CONFIG = json.load(f)

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
        # Map Apify fields to our matcher expectations
        jobs.append({
            "title": item.get("title", ""),
            "company": item.get("companyName", ""),
            "description": item.get("description", "") or item.get("descriptionText", ""),
            "location": item.get("location", ""),
            # Apify often uses 'link' or 'applyUrl'
            "url": item.get("jobUrl") or item.get("url") or item.get("link") or item.get("applyUrl") or "#"
        })
    return jobs

def send_email(results):
    if not results:
        print("No matches found to email.")
        return

    print(f"Sending email with {len(results)} jobs...")
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    msg['Subject'] = "Your Daily Top 10 Job Matches"

    # Build HTML body
    html_content = "<h2>🔥 Top matches for you today</h2><ul>"
    
    for job in results[:10]:
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
    matches = match_jobs(resume_text, clean_jobs)
    print(f"Ranked {len(matches)} jobs.")

    # 5. Email
    # Only send if we have matches and a password set
    if EMAIL_PASSWORD and "App Password" not in EMAIL_PASSWORD:
        send_email(matches)
    else:
        print("Skipping email send. Please set EMAIL_PASSWORD in .env to send real emails.")

if __name__ == "__main__":
    main()
