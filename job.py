import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import json
import os

# --------------------------------------
# SETTINGS
# --------------------------------------
IST = pytz.timezone("Asia/Kolkata")
now = datetime.now(IST)
one_hour_ago = now - timedelta(hours=1)

KEYWORDS = ["devops", "sre", "cloud", "platform", "infrastructure"]
OUTPUT_DIR = "job_reports"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------
# SCRAPER HELPER
# --------------------------------------
def keyword_match(text):
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in KEYWORDS)

# --------------------------------------
# 1) INDEED SCRAPER
# --------------------------------------
def scrape_indeed():
    jobs = []
    url = "https://in.indeed.com/jobs?q=devops&l=Bangalore&fromage=1"

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    for card in soup.select("div.job_seen_beacon"):
        title_el = card.select_one("h2 span")
        company_el = card.select_one(".companyName")
        link_el = card.select_one("a")

        if not title_el or not company_el or not link_el:
            continue

        title = title_el.text.strip()
        company = company_el.text.strip()
        link = "https://in.indeed.com" + link_el.get("href")

        # Time filter: only "Just posted" / "1 hour" / "Few minutes"
        date_text = card.select_one(".date").text.lower()

        if not ("just" in date_text or "hour" in date_text or "minute" in date_text):
            continue

        if keyword_match(title):
            jobs.append({
                "title": title,
                "company": company,
                "location": "Bangalore",
                "link": link,
                "source": "Indeed"
            })

    return jobs

# --------------------------------------
# 2) LINKEDIN (public, limited)
# --------------------------------------
def scrape_linkedin():
    jobs = []
    url = ("https://www.linkedin.com/jobs/search/"
           "?keywords=devops&location=Bangalore%2C%20Karnataka%2C%20India&f_TPR=r86400")

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    for card in soup.select(".base-card"):
        title_el = card.select_one(".base-search-card__title")
        company_el = card.select_one(".base-search-card__subtitle")
        link_el = card.select_one("a.base-card__full-link")

        if not title_el or not company_el or not link_el:
            continue

        title = title_el.text.strip()
        company = company_el.text.strip()
        link = link_el.get("href")

        if keyword_match(title):
            jobs.append({
                "title": title,
                "company": company,
                "location": "Bangalore",
                "link": link,
                "source": "LinkedIn"
            })

    return jobs

# --------------------------------------
# 3) ANGELLIST / WELLFOUND
# --------------------------------------
def scrape_angellist():
    jobs = []
    url = "https://wellfound.com/jobs?location=Bangalore&keywords=DevOps&remote=true"

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    for card in soup.select(".job-listing"):
        title_el = card.select_one(".job-title")
        company_el = card.select_one(".company-title")
        link_el = card.select_one("a")

        if not title_el or not company_el or not link_el:
            continue

        title = title_el.text.strip()
        company = company_el.text.strip()
        link = "https://wellfound.com" + link_el.get("href")

        if keyword_match(title):
            jobs.append({
                "title": title,
                "company": company,
                "location": "Bangalore / Remote",
                "link": link,
                "source": "AngelList"
            })

    return jobs

# --------------------------------------
# 4) YC STARTUP JOBS (API)
# --------------------------------------
def scrape_yc():
    jobs = []
    url = "https://www.ycombinator.com/jobs/api/jobs?query=DevOps&Bangalore"

    try:
        r = requests.get(url)
        data = r.json()
    except:
        return jobs

    for item in data:
        title = item.get("title", "")
        if not keyword_match(title):
            continue

        jobs.append({
            "title": item.get("title"),
            "company": item.get("company_name"),
            "location": item.get("location", "Unknown"),
            "link": "https://ycombinator.com" + item.get("job_post_url", ""),
            "source": "YCombinator"
        })

    return jobs

# --------------------------------------
# 5) CUTSHORT
# --------------------------------------
def scrape_cutshort():
    jobs = []
    url = "https://cutshort.io/jobs/devops-jobs-in-bangalore"

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    for card in soup.select(".job-card"):
        title_el = card.select_one(".job-title")
        company_el = card.select_one(".h5")
        link_el = card.select_one("a")

        if not title_el or not company_el or not link_el:
            continue

        title = title_el.text.strip()
        company = company_el.text.strip()
        link = "https://cutshort.io" + link_el.get("href")

        if keyword_match(title):
            jobs.append({
                "title": title,
                "company": company,
                "location": "Bangalore",
                "link": link,
                "source": "CutShort"
            })

    return jobs

# --------------------------------------
# OUTPUT FORMATS
# --------------------------------------
def save_txt(jobs):
    with open(os.path.join(OUTPUT_DIR, "job_report.txt"), "w", encoding="utf-8") as f:
        for j in jobs:
            f.write(f"{j['title']} — {j['company']}\n")
            f.write(f"Location: {j['location']}\n")
            f.write(f"Apply: {j['link']}\n")
            f.write(f"Source: {j['source']}\n")
            f.write("-" * 60 + "\n")

def save_md(jobs):
    md = [f"# Daily DevOps/SRE Job Report\nGenerated: **{now}**\n\n"]
    for j in jobs:
        md.append(f"### 🔹 {j['title']} — {j['company']}")
        md.append(f"- **Location:** {j['location']}")
        md.append(f"- **Apply:** [{j['link']}]({j['link']})")
        md.append(f"- **Source:** {j['source']}\n")
    with open(os.path.join(OUTPUT_DIR, "job_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

def save_json(jobs):
    with open(os.path.join(OUTPUT_DIR, "job_report.json"), "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4)

def save_html(jobs):
    html = ["<html><body><h2>Daily DevOps/SRE Job Report</h2>"]
    for j in jobs:
        html.append("<div style='padding:12px;border:1px solid #ccc;margin:10px;border-radius:8px;'>")
        html.append(f"<h3>{j['title']} — {j['company']}</h3>")
        html.append(f"<p><b>Location:</b> {j['location']}</p>")
        html.append(f"<a href='{j['link']}'>Apply Here</a>")
        html.append(f"<p><i>Source: {j['source']}</i></p></div>")
    html.append("</body></html>")
    with open(os.path.join(OUTPUT_DIR, "job_report.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(html))

# --------------------------------------
# MAIN
# --------------------------------------
def main():
    print("Fetching jobs…")

    all_jobs = []
    all_jobs += scrape_indeed()
    all_jobs += scrape_linkedin()
    all_jobs += scrape_angellist()
    all_jobs += scrape_yc()
    all_jobs += scrape_cutshort()

    print(f"Found {len(all_jobs)} jobs.")

    save_txt(all_jobs)
    save_md(all_jobs)
    save_json(all_jobs)
    save_html(all_jobs)

    print(f"Reports saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
