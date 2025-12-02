import requests
from bs4 import BeautifulSoup
import re

SOURCES = {
    "LinkedIn": "site:linkedin.com/jobs devops engineer bangalore last 24 hours",
    "Naukri": "site:naukri.com devops engineer bangalore last 24 hours",
    "Indeed": "site:indeed.com devops engineer bangalore last 24 hours",
    "Glassdoor": "site:glassdoor.com devops engineer bangalore last 24 hours"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def google_search(query):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    results = []
    for g in soup.select("div.tF2Cxc"):
        title = g.select_one("h3").text if g.select_one("h3") else "No title"
        link = g.select_one("a")["href"] if g.select_one("a") else ""
        snippet = g.select_one(".VwiC3b").text if g.select_one(".VwiC3b") else ""
        results.append({"title": title, "link": link, "snippet": snippet})
    return results


def remove_duplicates(jobs):
    seen = set()
    unique = []
    for job in jobs:
        if job["link"] not in seen:
            unique.append(job)
            seen.add(job["link"])
    return unique


def main():
    all_jobs = []

    print("🔍 Fetching jobs from Google (LinkedIn + Naukri + Indeed + Glassdoor)...")

    for source, query in SOURCES.items():
        print(f"\n➡ Searching: {source}")
        res = google_search(query)

        for job in res:
            job["source"] = source
            all_jobs.append(job)

    all_jobs = remove_duplicates(all_jobs)

    # Save to file
    with open("jobs_report.txt", "w", encoding="utf-8") as f:
        f.write("DAILY DEVOPS / SRE JOB REPORT (LAST 24 HOURS)\n")
        f.write("=" * 60 + "\n\n")

        for job in all_jobs:
            f.write(f"Source: {job['source']}\n")
            f.write(f"Title: {job['title']}\n")
            f.write(f"Link: {job['link']}\n")
            f.write(f"Snippet: {job['snippet']}\n")
            f.write("-" * 40 + "\n")

    print("\n✅ Job report created: jobs_report.txt")
    print(f"📌 Total jobs found: {len(all_jobs)}")


if __name__ == "__main__":
    main()
