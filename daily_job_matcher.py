import json
import re

# Load config rules from your JSON file
with open("config.json") as f:
    CONFIG = json.load(f)

def preprocess(text):
    return re.sub(r"[^a-zA-Z0-9 ]", " ", text).lower()

def score_job(resume_text, job):
    resume = preprocess(resume_text)
    
    # Load settings from config
    settings = CONFIG.get("settings", {})
    max_exp = settings.get("max_experience_years", 2)
    boost_score = settings.get("fresh_grad_boost_score", 10)
    keyword_score = settings.get("keyword_match_score", 5)
    
    # 1. Negative Filter (Exclude Keywords)
    title_lower = job['title'].lower()
    exclude_keywords = CONFIG.get("exclude_keywords", [])
    if any(kw.lower() in title_lower for kw in exclude_keywords):
        return 0

    # 2. Seniority Filter
    seniority_keywords = CONFIG.get("seniority_keywords", [])
    
    if any(kw in title_lower for kw in seniority_keywords):
        return 0

    # 2. Experience Filter
    desc_lower = job['description'].lower()
    
    # Regex explanation:
    # \b(\d+)            -> Match start number (Group 1)
    # \s*                -> optional space
    # (?:                -> start optional range group
    #   (?:-|to)         -> match hyphen or 'to'
    #   \s*              -> optional space
    #   (\d+)            -> match end number (Group 2)
    # )?                 -> range is optional
    # \s*                -> optional space
    # (?:                -> start optional 'plus' group
    #    \+|plus         -> match + or plus
    # )?                 -> optional
    # \s*                -> optional space
    # years?             -> match year or years
    experience_pattern = r'\b(\d+)\s*(?:(?:-|to)\s*(\d+))?\s*(?:(\+|plus))?\s*years?'
    
    matches = re.finditer(experience_pattern, desc_lower)
    for match in matches:
        # Check context: if preceded by "within" (e.g. "within 2 years"), ignore match.
        start_idx = match.start()
        preceding_text = desc_lower[max(0, start_idx-10):start_idx]
        if "within" in preceding_text:
            continue

        num1 = int(match.group(1))
        # Logic: If start experience >= max_exp (default 2), filter it out.
        if num1 >= max_exp:
            return 0
            
    job_text = preprocess(
        f"{job['title']} {job['company']} {job['description']} {job['location']}"
    )

    score = 0

    # Fresh Grad / Entry Level Boost
    fresh_grad_keywords = CONFIG.get("fresh_grad_keywords", [])
    if any(kw in job_text for kw in fresh_grad_keywords):
        score += boost_score

    # Keyword Matching
    keywords = CONFIG.get("keywords", [])
    for kw in keywords:
        pattern = r"\b" + re.escape(kw.lower()) + r"\b"
        if re.search(pattern, job_text) and re.search(pattern, resume):
            score += keyword_score

    # Simple similarity scoring
    resume_words = set(resume.split())
    job_words = set(job_text.split())
    overlap = len(resume_words & job_words)

    score += overlap / 10  # scaling factor

    return score

def match_jobs(resume_text, jobs):
    results = []
    for job in jobs:
        s = score_job(resume_text, job)
        results.append({
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "url": job["url"],
            "match_score": s  # Renamed from "score" to "match_score"
        })
    
    # Sort descending by best score
    results = sorted(results, key=lambda x: x["match_score"], reverse=True)
    return results
