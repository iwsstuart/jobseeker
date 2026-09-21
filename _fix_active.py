# One-time repair: Wherobots/Carto/Inspiration Mobility were inserted
# inactive by an old version of seed.py, before their fetchers existed.
# seed()'s upsert deliberately never overwrites `active` on conflict (to
# protect manual toggles via onboard.py), so those stale values can't
# self-heal — this corrects them directly, once. Delete this file and its
# call in run.py after it's confirmed to have run in CI.
from db import get_connection, init_db

NAMES = ("Wherobots", "Carto", "Inspiration Mobility")


def fix_active():
    init_db()
    conn = get_connection()
    placeholders = ",".join("?" * len(NAMES))
    conn.execute(
        f"UPDATE companies SET active = 1 WHERE name IN ({placeholders}) AND active = 0",
        NAMES,
    )
    conn.commit()
    changed = conn.total_changes
    conn.close()
    print(f"fix_active: {changed} row(s) corrected.")


if __name__ == "__main__":
    fix_active()
