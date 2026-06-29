import requests

_BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch_jobs(board_token: str) -> list[dict]:
    url = _BASE.format(token=board_token)
    resp = requests.get(url, params={"content": "true"}, timeout=30)
    resp.raise_for_status()
    jobs = []
    for job in resp.json().get("jobs", []):
        jobs.append({
            "external_id": str(job["id"]),
            "title": job["title"],
            "url": job.get("absolute_url"),
            "raw_description": job.get("content"),
        })
    return jobs
