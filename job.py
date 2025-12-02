import os
import requests
from datetime import datetime, timezone, timedelta
from textwrap import indent

# ========= CONFIG =========

JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")
JSEARCH_HOST = "jsearch.p.rapidapi.com"

SEARCH_QUERIES = [
    "DevOps Engineer",
    "Site Reliability Engineer",
    "SRE",
]

LOCATION = "Bangalore, India"

# How many hours back to keep (approx "last hours")
MAX_JOB_AGE_HOURS = 6

MAX_JOBS = 50

# Set to ["LinkedIn"] if you want to EXCLUDE LinkedIn jobs
EXCLUDED_PUBLISHERS = []  # e.g. ["LinkedIn"]

# Keywords to roughly match your stack
MUST_KEYWORDS = ["devops", "sre", "kubernetes", "aws", "docker", "terraform"]

CANDIDATE_NAME = "Abin"  # used in outreach messages
OUTPUT_FILE = "jobs_report.txt"

# ========= CORE FUNCTIONS =========


def fetch_jobs_from_jsearch(query: str, location: str):
    """
    Uses JSearch API via RapidAPI to fetch jobs.
    Docs indicate /search endpoint with query + location. :contentReference[oaicite:1]{index=1}
    """
    if not JSEARCH_API_KEY:
        raise RuntimeError(
            "JSEARCH_API_KEY environment variable is not set. "
            "Set it to your RapidAPI key for the JSearch API."
        )

    url = f"https://{JSEARCH_HOST}/search"
    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": JSEARCH_HOST,
    }
    # We keep params simple; JSearch supports many filters.
    params = {
        "query": f"{query} in {location}",
        "page": "1",
        "num_pages": "1",
        "date_posted": "today",  # we will post-filter by datetime
    }

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def parse_posted_datetime(job: dict):
    """
    Parse job_posted_at_datetime_utc (if present) to datetime.
    """
    dt_str = job.get("job_posted_at_datetime_utc")
    if not dt_str:
        return None
    try:
        # Example format: "2024-07-05T12:36:32.000Z" :contentReference[oaicite:2]{index=2}
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def is_recent(job: dict, max_age_hours: int) -> bool:
    posted = parse_posted_datetime(job)
    if not posted:
        return False
    now = datetime.now(timezone.utc)
    return now - posted <= timedelta(hours=max_age_hours)


def matches_keywords(job: dict) -> bool:
    text = (
        (job.get("job_title") or "") + " " +
        (job.get("job_description") or "")
    ).lower()
    return any(kw.lower() in text for kw in MUST_KEYWORDS)


def is_allowed_publisher(job: dict) -> bool:
    publisher = (job.get("job_publisher") or "").strip()
    return publisher not in EXCLUDED_PUBLISHERS


def simplify_job(job: dict) -> dict:
    return {
        "title": job.get("job_title", "N/A"),
        "company": job.get("employer_name", "N/A"),
        "location": job.get("job_location", "N/A"),
        "publisher": job.get("job_publisher", "N/A"),
        "apply_link": job.get("job_apply_link")
                       or job.get("job_google_link")
                       or "#",
        "description": job.get("job_description", ""),
        "posted_utc": job.get("job_posted_at_datetime_utc", ""),
    }


def collect_jobs():
    all_jobs = []

    for q in SEARCH_QUERIES:
        try:
            jobs = fetch_jobs_from_jsearch(q, LOCATION)
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"[WARN] Failed to fetch for query '{q}': {e}")

    # Deduplicate by job_id if present
    dedup = {}
    for j in all_jobs:
        job_id = j.get("job_id") or id(j)
        dedup[job_id] = j

    jobs = list(dedup.values())

    # Filter by recency, keywords, and publisher
    filtered = [
        j for j in jobs
        if is_recent(j, MAX_JOB_AGE_HOURS)
        and matches_keywords(j)
        and is_allowed_publisher(j)
    ]

    # Simplify & trim
    simplified = [simplify_job(j) for j in filtered]
    return simplified[:MAX_JOBS]


# ========= FORMATTING =========


def generate_email_body(jobs):
    if not jobs:
        return (
            "Subject: DevOps / SRE job digest – no fresh matches in the last "
            f"{MAX_JOB_AGE_HOURS} hours\n\n"
            f"No suitable DevOps / SRE roles were found for Bangalore in the last "
            f"{MAX_JOB_AGE_HOURS} hours based on the current filters.\n"
        )

    subject = (
        f"Subject: DevOps / SRE roles – last {MAX_JOB_AGE_HOURS}h – "
        f"{len(jobs)} matches\n"
    )

    header = (
        "Hi,\n\n"
        "Here is your fresh DevOps / SRE job digest from the last "
        f"{MAX_JOB_AGE_HOURS} hours for Bangalore:\n\n"
    )

    lines = []
    for idx, job in enumerate(jobs, start=1):
        desc_snippet = (job["description"] or "").strip().replace("\n", " ")
        if len(desc_snippet) > 260:
            desc_snippet = desc_snippet[:260].rsplit(" ", 1)[0] + "..."

        lines.append(
            f"{idx}. {job['title']} – {job['company']}\n"
            f"   Location: {job['location']}\n"
            f"   Publisher: {job['publisher']}\n"
            f"   Posted (UTC): {job['posted_utc']}\n"
            f"   Apply: {job['apply_link']}\n"
            f"   Summary: {desc_snippet}\n"
        )

    footer = (
        "\nRegards,\n"
        "Your DevOps Job Bot\n"
    )

    return subject + "\n" + header + "\n".join(lines) + footer


def generate_linkedin_messages(jobs, candidate_name=CANDIDATE_NAME):
    """
    Returns a list of (job, message_text) tuples.
    """
    messages = []

    for job in jobs:
        title = job["title"]
        company = job["company"]
        location = job["location"]
        publisher = job["publisher"]

        # Very short, easy-to-paste outreach
        msg = (
            f"Hi {{Name}},\n\n"
            f"I came across the *{title}* role at *{company}* in {location} "
            f"(saw it via {publisher}). I have 2–5 years of experience with "
            f"AWS, Kubernetes, Docker, Terraform and CI/CD (GitHub Actions) "
            f"building and operating cloud-native systems.\n\n"
            f"I'd love to explore whether my DevOps/SRE background could be a "
            f"good fit for the team. If you’re the right person for this role "
            f"or can connect me with the hiring manager, I’d really appreciate it.\n\n"
            f"Best,\n"
            f"{candidate_name}\n"
        )

        messages.append((job, msg))

    return messages


def write_report_file(jobs, email_body, linkedin_messages):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("=== EMAIL SUMMARY (paste this into Gmail) ===\n\n")
        f.write(email_body)
        f.write("\n\n\n=== LINKEDIN OUTREACH MESSAGES ===\n\n")

        if not linkedin_messages:
            f.write("No jobs -> no LinkedIn messages.\n")
            return

        for idx, (job, msg) in enumerate(linkedin_messages, start=1):
            header = (
                f"[{idx}] {job['title']} – {job['company']} "
                f"({job['location']})\n"
                f"Apply: {job['apply_link']}\n\n"
            )
            f.write(header)
            f.write(indent(msg, "    "))
            f.write("\n" + "-" * 60 + "\n\n")


# ========= MAIN =========

def main():
    print("[INFO] Collecting jobs...")
    jobs = collect_jobs()
    print(f"[INFO] Found {len(jobs)} jobs after filtering.")

    email_body = generate_email_body(jobs)
    linkedin_messages = generate_linkedin_messages(jobs)

    write_report_file(jobs, email_body, linkedin_messages)
    print(f"[INFO] Report written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
