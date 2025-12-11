# Daily Job Scraper & Matcher

A personalized job hunting bot that scrapes LinkedIn jobs via Apify, matches them against your resume using keyword scoring and experience filtering, and emails you the top results.

## Features
- **Smart Filtering**: Automatically removes jobs requiring high years of experience (customizable).
- **Keyword Scoring**: Boosts jobs that match your skills (Python, SQL, etc.) and prioritizes fresh grad/entry-level roles.
- **Context Aware**: Distinguishes between "2 years experience" (filtered) vs "within 2 years" (kept).
- **Daily Reporting**: Emails you a summary of the top 10 matches.

## Apify Setup
This project uses **Apify** to scrape data from LinkedIn.

1.  **Create an Account**: Go to [Apify](https://apify.com/) and sign up.
2.  **Get API Token**: Go to Settings > Integrations and copy your Personal API Token.
3.  **Choose an Actor**:
    - By default, this project uses the actor **`curious_coder/linkedin-jobs-scraper`**.
    - You need to "Rent" or "Start" this actor in your Apify console at least once to ensure it's active (or just rely on the API call).
    - **Note**: You are free to swap this for any other LinkedIn scraper actor on Apify. If you do, update line 32 in `daily_bot.py` with the new Actor ID/URL structure.

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   APIFY_TOKEN=your_apify_token_here
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   ```

3. **Resume**
   Place your resume PDF in the project folder and update `config.json` with its filename.

## Customization
All settings are managed in `config.json`.

- **`settings`**:
    - `max_experience_years`: Filter out jobs requiring more than this (e.g., set to 3 to keep 1-2 year roles).
    - `top_results_limit`: How many jobs to email you (e.g., 10, 20).
    - `fresh_grad_boost_score`: Bonus points for "fresh grad" / "junior" roles.
    - `resume_path`: Path to your PDF resume.
- **`apify`**:
    - `max_items`: How many jobs to fetch from LinkedIn (e.g. 100).
- **`job_queries`**: Add or remove LinkedIn search URLs.
- **`keywords`**: Add skills you want to match (e.g., "React", "AWS").

## Usage
Run the script manually:
```bash
python3 daily_bot.py
```

## Automation (Daily Schedule)
To run this automatically (e.g., every day at 9 AM) on macOS/Linux:

1. Open your cron schedule:
   ```bash
   crontab -e
   ```
2. Add the following line (replace `/path/to/project` with your actual full path):
   ```bash
   0 9 * * * cd "/path/to/project" && /usr/bin/python3 daily_bot.py >> cron_log.txt 2>&1
   ```
   **Breakdown of `0 9 * * *`:**
   - `0`: Minute (0-59)
   - `9`: Hour (0-23, 24-hour command)
   - `*`: Day of Month
   - `*`: Month
   - `*`: Day of Week

   *Example: To run at 5:30 PM, use `30 17 * * *`.*

3. **Save and Exit**:
   - **If you are in Vim** (default on Mac):
     - Press `Esc` key.
     - Type `:wq` (write and quit).
     - Press `Enter`.
   - **If you are in Nano**:
     - Press `Ctrl + X`.
     - Press `Y` to confirm.
     - Press `Enter` to save.

