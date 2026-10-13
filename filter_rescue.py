"""Re-check previously filtered_out jobs against the current title_filter.py
ruleset, and rescue any that would no longer be excluded.

filter.py's run_filter() only ever looks at jobs with processing_status =
'new' -- once a job is flipped to 'filtered_out', no future pipeline run
revisits it. So loosening the exclude/allow lists (removing an over-broad
term, adding a new allow-term) has no effect on jobs already filtered under
older rules unless this script is run deliberately.

Defaults to a dry run (just prints what WOULD change). Pass --apply to
actually write the rescued jobs back to processing_status = 'new'. Never
invoked by the normal cron -- this is an explicit, manually-triggered action,
ideally after reviewing filter_compare.py's --diff output first.
"""
from db import get_connection
from title_filter import classify_title, RULESET_VERSION, ensure_ruleset_recorded


def run_rescue(dry_run=True):
    conn = get_connection()
    ensure_ruleset_recorded(conn)

    jobs = conn.execute(
        """SELECT id, title FROM jobs
           WHERE processing_status = 'filtered_out'
             AND (filter_ruleset_version IS NULL OR filter_ruleset_version != %s)""",
        (RULESET_VERSION,),
    ).fetchall()

    rescued = 0
    for job in jobs:
        verdict, reason = classify_title(job["title"])
        if verdict == "keep":
            rescued += 1
            print(f"  [{job['id']}] {job['title']!r} -> rescued ({reason or 'no exclude term matches'})")
            if not dry_run:
                conn.execute(
                    """UPDATE jobs SET processing_status = 'new',
                           filter_reason = %s, filter_ruleset_version = %s
                       WHERE id = %s""",
                    (reason, RULESET_VERSION, job["id"]),
                )
        elif not dry_run:
            # Still excluded -- just refresh the version stamp so it isn't
            # re-scanned again next time unless the rules change again.
            conn.execute(
                "UPDATE jobs SET filter_reason = %s, filter_ruleset_version = %s WHERE id = %s",
                (reason, RULESET_VERSION, job["id"]),
            )

    if not dry_run:
        conn.commit()
    conn.close()
    print(f"\n{'[DRY RUN] ' if dry_run else ''}{rescued} rescued out of {len(jobs)} re-checked.")


if __name__ == "__main__":
    import sys

    run_rescue(dry_run="--apply" not in sys.argv)
