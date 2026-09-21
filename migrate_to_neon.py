# One-time migration: load a SQLite snapshot (exported from GitHub Actions
# cache) into a fresh Neon Postgres database. Run once during the Neon
# migration, then safe to delete — not meant to be a permanent fixture.
#
# Usage: DATABASE_URL=<neon connection string> python3 migrate_to_neon.py [path/to/jobseeker.db]
import argparse
import json
import sqlite3

from psycopg.types.json import Jsonb

from db import get_connection, init_db

TABLES = ["companies", "jobs", "job_extractions", "match_results"]

COLUMNS = {
    "companies": ["id", "name", "careers_url", "ats", "ats_identifier", "active"],
    "jobs": [
        "id", "company_id", "external_id", "title", "url", "raw_description",
        "first_seen_at", "last_seen_at", "status", "processing_status",
    ],
    "job_extractions": ["job_id", "skills", "experience_level", "key_requirements", "extracted_at"],
    "match_results": ["job_id", "is_match", "reasoning", "notified_at", "evaluated_at"],
}

BOOL_COLUMNS = {"companies": {"active"}, "match_results": {"is_match"}}
JSON_COLUMNS = {"job_extractions": {"skills", "key_requirements"}}
# tables with an auto-generated id whose sequence needs resetting after a load that specifies ids explicitly
IDENTITY_TABLES = {"companies": "id", "jobs": "id"}


def migrate(sqlite_path: str):
    sconn = sqlite3.connect(sqlite_path)
    sconn.row_factory = sqlite3.Row

    pconn = get_connection()
    init_db()

    for table in TABLES:
        cols = COLUMNS[table]
        rows = sconn.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()

        for row in rows:
            values = []
            for col in cols:
                val = row[col]
                if col in BOOL_COLUMNS.get(table, set()):
                    val = bool(val)
                elif col in JSON_COLUMNS.get(table, set()) and val is not None:
                    val = Jsonb(json.loads(val))
                values.append(val)
            placeholders = ", ".join(["%s"] * len(cols))
            overriding = "OVERRIDING SYSTEM VALUE" if table in IDENTITY_TABLES else ""
            pconn.execute(
                f"INSERT INTO {table} ({', '.join(cols)}) {overriding} VALUES ({placeholders})",
                values,
            )

        pconn.commit()

        sqlite_count = sconn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        pg_count = pconn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()["count"]
        assert sqlite_count == pg_count, f"{table}: sqlite has {sqlite_count} rows, Postgres has {pg_count}"
        print(f"{table}: migrated {pg_count} rows (verified).")

    for table, id_col in IDENTITY_TABLES.items():
        pconn.execute(
            f"SELECT setval(pg_get_serial_sequence(%s, %s), COALESCE((SELECT MAX({id_col}) FROM {table}), 1))",
            (table, id_col),
        )
    pconn.commit()

    sconn.close()
    pconn.close()
    print("Migration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("sqlite_path", nargs="?", default="jobseeker.db")
    args = parser.parse_args()
    migrate(args.sqlite_path)
