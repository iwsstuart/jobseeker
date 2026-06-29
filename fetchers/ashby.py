import requests

_BASE = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


def fetch_jobs(company_slug: str) -> list[dict]:
    url = _BASE.format(slug=company_slug)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    jobs = []
    for job in resp.json().get("jobs", []):
        if not job.get("isListed", True):
            continue
        jobs.append({
            "external_id": job["id"],
            "title": job["title"],
            "url": job.get("jobUrl"),
            "raw_description": job.get("descriptionHtml"),
        })
    return jobs
