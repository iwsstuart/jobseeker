from datetime import datetime, timezone

from db import get_connection, init_db
from fetchers import greenhouse, ashby

FETCHERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "ashby": ashby.fetch_jobs,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def fetch_company(conn, company):
    ats = company["ats"]
    fetcher = FETCHERS.get(ats)
    if not fetcher:
        print(f"  [{company['name']}] No fetcher for ATS '{ats}', skipping.")
        return

    print(f"  [{company['name']}] Fetching via {ats} (identifier: {company['ats_identifier']})...")
    try:
        jobs = fetcher(company["ats_identifier"])
    except Exception as e:
        print(f"  [{company['name']}] ERROR: {e}")
        return

    now = _now()
    seen_ids = set()

    for job in jobs:
        ext_id = job["external_id"]
        seen_ids.add(ext_id)
        existing = conn.execute(
            "SELECT id FROM jobs WHERE company_id = ? AND external_id = ?",
            (company["id"], ext_id),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE jobs SET last_seen_at = ?, status = 'open' WHERE id = ?",
                (now, existing["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO jobs
                       (company_id, external_id, title, url, raw_description,
                        first_seen_at, last_seen_at, status, processing_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'open', 'new')""",
                (company["id"], ext_id, job["title"], job["url"], job["raw_description"], now, now),
            )

    # Jobs no longer in the feed → mark closed
    if seen_ids:
        placeholders = ",".join("?" * len(seen_ids))
        conn.execute(
            f"""UPDATE jobs SET status = 'closed'
                WHERE company_id = ? AND status = 'open'
                AND external_id NOT IN ({placeholders})""",
            (company["id"], *seen_ids),
        )
    else:
        conn.execute(
            "UPDATE jobs SET status = 'closed' WHERE company_id = ? AND status = 'open'",
            (company["id"],),
        )

    conn.commit()
    print(f"  [{company['name']}] {len(jobs)} jobs fetched.")


def main():
    init_db()
    conn = get_connection()
    companies = conn.execute("SELECT * FROM companies WHERE active = 1").fetchall()

    if not companies:
        print("No active companies found. Run seed.py first.")
        return

    print(f"Fetching jobs for {len(companies)} active companies...\n")
    for company in companies:
        fetch_company(conn, company)

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
