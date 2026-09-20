import requests

_LIST = "https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs"
_DETAIL = "https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs/{uuid}"


def fetch_jobs(slug: str) -> list[dict]:
    listing = requests.get(_LIST.format(slug=slug), timeout=30)
    listing.raise_for_status()

    # The list endpoint repeats a job once per work location, sharing the
    # same uuid — dedupe here since the DB has no location field to keep
    # the repeats for.
    seen = {}
    for job in listing.json():
        seen.setdefault(job["uuid"], job)

    jobs = []
    for uuid, job in seen.items():
        detail = requests.get(_DETAIL.format(slug=slug, uuid=uuid), timeout=30)
        detail.raise_for_status()
        description = detail.json().get("description") or {}
        jobs.append({
            "external_id": uuid,
            "title": job["name"],
            "url": job.get("url"),
            "raw_description": description.get("company"),
        })
    return jobs
