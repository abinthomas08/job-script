import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

OUTPUT_FILE = "jobs_report.txt"
CANDIDATE_NAME = "Abin"

# Keywords we care about
KEYWORDS = [
    "devops", "sre", "site reliability", "kubernetes",
    "aws", "docker", "terraform", "ci/cd", "cloud"
]

# Recent jobs filter
MAX_HOURS = 24  # last 24 hours


# ============================
# 1) INDEED SCRAPER
# ============================
def scrape_indeed():
    print("➡ Scraping Indeed...")
    url = "https://in.indeed.com/jobs?q=devops&l=Bangalore&fromage=1"

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    results = []
    cards = soup.select("div.job_seen_beacon")

    for card in cards:
        title_el = card.select_one("h2 span")
        company_el = card.select_one(".companyName")
        link_el = card.select_one("a")

        if not title_el or not link_el:
            continue

        title = title_el.text.strip()
        company = company_el.text.strip() if company_el else "Unknown"
        link = "https://in.indeed.com" + link_el["href"]

        # time filter
        date_txt = card.select_one(".date").text.lower()
        if not ("just" in date_txt or "hour" in date_txt or "minute" in date_txt or "today" in date_txt):
            continue

        # keyword match
        if not any(k in title.lower() for k in KEYWORDS):
            continue

        results.append({
            "title": title,
            "company": company,
            "location": "Bangalore",
            "source": "Indeed",
            "link": link,
            "description": ""
        })

    return results


# ============================
# 2) NAUKRI SCRAPER
# ============================
def scrape_naukri():
    print("➡ Scraping Naukri...")
    url = "https://www.naukri.com/devops-jobs-in-bangalore?k=devops&fjt=0&last=1"

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    jobs = []
    cards = soup.select(".jobTuple")

    for card in cards:
        title_el = card.select_one("a.title")
        company_el = card.select_one(".subTitle")
        date_el = card.select_one(".job-post-day")

        if not title_el or not company_el:
            continue

        title = title_el.text.strip()
        company = company_el.text.strip()
        link = title_el["href"]

        date_txt = date_el.text.lower() if date_el else ""

        if not ("hour" in date_txt or "today" in date_txt or "just" in date_txt):
            continue

        if not any(k in title.lower() for k in KEYWORDS):
            continue

        jobs.append({
            "title": title,
            "company": company,
            "location": "Bangalore",
            "source": "Naukri",
            "link": link,
            "description": ""
        })

    return jobs


# ============================
# 3) MONSTER / FOUNDIT SCRAPER
# ============================
def scrape_monster():
    print("➡ Scraping Foundit/Monster...")
    url = "https://www.foundit.in/srp/results?query=devops&locations=bangalore"

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    jobs = []
    cards = soup.select(".srpResultCard")

    for card in cards:
        title_el = card.select_one("h3 a")
        company_el = card.select_one(".companyName")

        if not title_el or not company_el:
            continue

        title = title_el.text.strip()
        company = company_el.text.strip()
        link = title_el["href"]

        if not any(k in title.lower() for k in KEYWORDS):
            continue

        jobs.append({
            "title": title,
            "company": company,
            "location": "Bangalore",
            "source": "Monster",
            "link": link,
            "description": ""
        })

    return jobs


# ============================
# 4) Y COMBINATOR JOBS (NO KEY)
# ============================
def scrape_yc():
    print("➡ Scraping YC Startup Jobs...")
    url = "https://www.ycombinator.com/jobs/api/jobs?query=DevOps&query=Bangalore"

    try:
        data = requests.get(url).json()
    except:
        return []

    jobs = []
    for job in data:
        title = job.get("title", "")
        company = job.get("company_name", "")

        if not any(k in title.lower() for k in KEYWORDS):
            continue

        jobs.append({
            "title": job.get("title"),
            "company": company,
            "location": job.get("location", "Remote"),
            "source": "YCombinator",
            "link": "https://ycombinator.com" + job.get("job_post_url", ""),
            "description": job.get("description", "")[:200] + "..."
        })

    return jobs


# ============================
# FORMAT EMAIL + OUTREACH
# ============================

def build_email(jobs):
    subject = f"Subject: DevOps/SRE Job Report — {len(jobs)} roles (last 24h)"
    body = f"Hi {CANDIDATE_NAME},\n\nHere are the latest DevOps/SRE roles:\n\n"

    for i, j in enumerate(jobs, 1):
        body += (
            f"{i}. {j['title']} — {j['company']}\n"
            f"   Source: {j['source']}\n"
            f"   Location: {j['location']}\n"
            f"   Apply: {j['link']}\n\n"
        )

    return subject + "\n\n" + body


def build_linkedin_messages(jobs):
    msgs = []
    for j in jobs:
        msg = (
            f"Hi {{Name}},\n\n"
            f"I saw the *{j['title']}* role at *{j['company']}* via {j['source']}. "
            f"I have strong experience in Kubernetes, AWS, Docker, Terraform, and CI/CD.\n\n"
            f"Would love to connect and explore if this role is a fit.\n\n"
            f"Regards,\n{CANDIDATE_NAME}"
        )
        msgs.append((j, msg))
    return msgs


# ============================
# MAIN
# ============================

def main():
    indeed = scrape_indeed()
    naukri = scrape_naukri()
    monster = scrape_monster()
    yc = scrape_yc()

    jobs = indeed + naukri + monster + yc

    print(f"\n📌 Total jobs found: {len(jobs)}")

    email = build_email(jobs)
    outreach = build_linkedin_messages(jobs)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("=== EMAIL SUMMARY ===\n\n")
        f.write(email)
        f.write("\n\n=== LINKEDIN OUTREACH MESSAGES ===\n\n")

        for job, msg in outreach:
            f.write(f"{job['title']} — {job['company']} ({job['source']})\n")
            f.write(f"Apply: {job['link']}\n\n")
            f.write(msg + "\n\n---------------------\n\n")

    print(f"✅ Job report created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
