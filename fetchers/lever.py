import requests

_BASE = "https://api.lever.co/v0/postings/{slug}"


def fetch_jobs(slug: str) -> list[dict]:
    url = _BASE.format(slug=slug)
    resp = requests.get(url, params={"mode": "json"}, timeout=30)
    resp.raise_for_status()
    jobs = []
    for job in resp.json():
        jobs.append({
            "external_id": str(job["id"]),
            "title": job["text"],
            "url": job.get("hostedUrl"),
            "raw_description": job.get("description"),
        })
    return jobs
