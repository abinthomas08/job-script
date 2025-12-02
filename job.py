import os
import requests
from datetime import datetime, timezone, timedelta

# Your API key
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")
JSEARCH_HOST = "jsearch.p.rapidapi.com"

# Expand search queries to capture more jobs across platforms
SEARCH_QUERIES = [
    "DevOps Engineer",
    "Site Reliability Engineer",
    "SRE",
    "Cloud Engineer",
    "Platform Engineer",
    "Infrastructure Engineer",
    "CI/CD Engineer",
    "Kubernetes Engineer",
    "AWS Engineer",
]

LOCATION = "Bangalore, India"

# Increase to last 24 hours
MAX_JOB_AGE_HOURS = 24

# Number of results to keep
MAX_JOBS = 50

# If you want EVERYTHING (including LinkedIn), keep this empty:
EXCLUDED_PUBLISHERS = []  # E.g. ["LinkedIn"] to block LinkedIn

# Must contain one of these keywords
MUST_KEYWORDS = ["devops", "sre", "kubernetes", "aws", "docker", "terraform"]

OUTPUT_FILE = "jobs_report.txt"
CANDIDATE_NAME = "Abin"


def fetch_jobs(query, location):
    if not JSEARCH_API_KEY:
        raise RuntimeError("Set JSEARCH_API_KEY env variable")

    url = f"https://{JSEARCH_HOST}/search"
    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": JSEARCH_HOST
    }
    params = {
        "query": f"{query} in {location}",
        "page": "1",
        "num_pages": "1",
        "date_posted": "today"
    }

    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json().get("data", [])


def parse_utc(dt):
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except:
        return None


def is_recent(job):
    posted = parse_utc(job.get("job_posted_at_datetime_utc"))
    if not posted:
        return False
    return (datetime.now(timezone.utc) - posted) <= timedelta(hours=MAX_JOB_AGE_HOURS)


def matches_keywords(job):
    text = (job.get("job_title","") + " " + job.get("job_description","")).lower()
    return any(k in text for k in MUST_KEYWORDS)


def allowed_publisher(job):
    return job.get("job_publisher") not in EXCLUDED_PUBLISHERS


def simplify(job):
    return {
        "title": job.get("job_title"),
        "company": job.get("employer_name"),
        "location": job.get("job_location"),
        "publisher": job.get("job_publisher"),
        "apply": job.get("job_apply_link") or job.get("job_google_link"),
        "posted": job.get("job_posted_at_datetime_utc"),
        "description": job.get("job_description","")[:200] + "..."
    }


def collect_jobs():
    all_jobs = []

    for q in SEARCH_QUERIES:
        print(f"Searching: {q}")
        try:
            all_jobs.extend(fetch_jobs(q, LOCATION))
        except Exception as e:
            print("Error:", e)

    # Remove duplicates
    unique = {}
    for j in all_jobs:
        jid = j.get("job_id") or id(j)
        unique[jid] = j

    jobs = list(unique.values())

    filtered = [
        j for j in jobs
        if is_recent(j)
        and matches_keywords(j)
        and allowed_publisher(j)
    ]

    return [simplify(j) for j in filtered][:MAX_JOBS]


def generate_email(jobs):
    subject = f"Subject: DevOps/SRE Job Digest ({len(jobs)} roles)"
    body = "Hi,\n\nHere are DevOps/SRE roles from multiple platforms (last 24 hours):\n\n"

    for i, j in enumerate(jobs, 1):
        body += (
            f"{i}. {j['title']} — {j['company']}\n"
            f"   Location: {j['location']}\n"
            f"   Source: {j['publisher']}\n"
            f"   Apply: {j['apply']}\n"
            f"   {j['description']}\n\n"
        )

    return subject + "\n\n" + body


def generate_outreach(jobs):
    msgs = []
    for job in jobs:
        msg = (
            f"Hi {{Name}},\n\n"
            f"I came across the *{job['title']}* job at *{job['company']}* via {job['publisher']}. "
            f"I have 3+ years of hands-on experience with AWS, Kubernetes, Docker, Terraform, and CI/CD pipelines.\n\n"
            f"I’d love to explore if I could be a good fit. Can we connect?\n\n"
            f"Regards,\n{CANDIDATE_NAME}"
        )
        msgs.append((job, msg))
    return msgs


def write_output(jobs, email, outreach):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("=== EMAIL SUMMARY ===\n\n")
        f.write(email)
        f.write("\n\n=== LINKEDIN MESSAGES ===\n\n")

        for i, (job, msg) in enumerate(outreach, 1):
            f.write(f"[{i}] {job['title']} — {job['company']} ({job['location']})\n")
            f.write(f"Source: {job['publisher']}\n")
            f.write(f"Apply: {job['apply']}\n\n")
            f.write(msg + "\n\n")
            f.write("-" * 50 + "\n\n")


def main():
    print("Fetching jobs…")
    jobs = collect_jobs()
    print(f"Found {len(jobs)} jobs from multiple platforms!")

    email = generate_email(jobs)
    outreach = generate_outreach(jobs)
    write_output(jobs, email, outreach)

    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
