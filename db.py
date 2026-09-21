import os

import psycopg
from psycopg.rows import dict_row


def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL environment variable not set.")
    return psycopg.connect(database_url, row_factory=dict_row)


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name            TEXT NOT NULL,
            careers_url     TEXT,
            ats             TEXT NOT NULL,
            ats_identifier  TEXT,
            active          BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_name ON companies(name)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            company_id         INTEGER NOT NULL REFERENCES companies(id),
            external_id        TEXT NOT NULL,
            title              TEXT NOT NULL,
            url                TEXT,
            raw_description    TEXT,
            first_seen_at      TEXT NOT NULL,
            last_seen_at       TEXT NOT NULL,
            status             TEXT NOT NULL DEFAULT 'open',
            processing_status  TEXT NOT NULL DEFAULT 'new',
            UNIQUE(company_id, external_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_extractions (
            job_id            INTEGER PRIMARY KEY REFERENCES jobs(id),
            skills            JSONB,
            experience_level  TEXT,
            key_requirements  JSONB,
            extracted_at      TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS match_results (
            job_id        INTEGER PRIMARY KEY REFERENCES jobs(id),
            is_match      BOOLEAN NOT NULL,
            reasoning     TEXT,
            notified_at   TEXT,
            evaluated_at  TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
