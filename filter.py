from db import get_connection
from title_filter import classify_title, RULESET_VERSION, ensure_ruleset_recorded


def run_filter():
    conn = get_connection()
    ensure_ruleset_recorded(conn)

    jobs = conn.execute(
        "SELECT id, title FROM jobs WHERE processing_status = 'new'"
    ).fetchall()

    filtered, kept = 0, 0
    for job in jobs:
        verdict, reason = classify_title(job["title"])
        if verdict == "exclude":
            conn.execute(
                """UPDATE jobs SET processing_status = 'filtered_out',
                       filter_reason = %s, filter_ruleset_version = %s
                   WHERE id = %s""",
                (reason, RULESET_VERSION, job["id"]),
            )
            print(f"  [{job['id']}] {job['title']!r} -> filtered_out ({reason})")
            filtered += 1
        else:
            if reason:  # allow-rescued keep, worth recording
                conn.execute(
                    "UPDATE jobs SET filter_reason = %s, filter_ruleset_version = %s WHERE id = %s",
                    (reason, RULESET_VERSION, job["id"]),
                )
            kept += 1

    conn.commit()
    conn.close()
    print(f"Filter complete: {filtered} filtered out, {kept} passed through.")


if __name__ == "__main__":
    run_filter()
