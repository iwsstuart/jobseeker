import requests

_BASE = "https://{subdomain}.pinpointhq.com/postings.json"


def fetch_jobs(subdomain: str) -> list[dict]:
    url = _BASE.format(subdomain=subdomain)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    jobs = []
    for job in resp.json().get("data", []):
        jobs.append({
            "external_id": str(job["id"]),
            "title": job["title"],
            "url": job.get("url"),
            "raw_description": job.get("description"),
        })
    return jobs
