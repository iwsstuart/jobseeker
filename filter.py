from db import get_connection

EXCLUDE_KEYWORDS = [
    # Sales
    "account executive",
    "account manager",
    "business development",
    "sales development",
    "sales director",
    "sales assist",
    # Recruiting / HR
    "recruiter",
    "sourcer",
    "talent acquisition",
    "hr business partner",
    # Legal / Procurement
    "paralegal",
    "procurement",
    # Accounting
    "accountant",
    "accounts receivable",
    # Clinical (Headway-specific)
    "licensed",
    "medical director",
    "medical coding",
    "payer partnerships",
    "care partnerships",
    # Design
    "product designer",
    "graphic designer",
    # Customer success / admin
    "customer success",
    "office manager",
    # Marketing
    "content marketing",
    # Catch-all
    "summer school",
    "general application",
    "talent community",
]


def should_filter(title: str) -> bool:
    lowered = title.lower()
    return any(kw in lowered for kw in EXCLUDE_KEYWORDS)


def run_filter():
    conn = get_connection()
    jobs = conn.execute(
        "SELECT id, title FROM jobs WHERE processing_status = 'new'"
    ).fetchall()

    filtered, kept = 0, 0
    for job in jobs:
        if should_filter(job["title"]):
            conn.execute(
                "UPDATE jobs SET processing_status = 'filtered_out' WHERE id = %s",
                (job["id"],),
            )
            filtered += 1
        else:
            kept += 1

    conn.commit()
    conn.close()
    print(f"Filter complete: {filtered} filtered out, {kept} passed through.")


if __name__ == "__main__":
    run_filter()
