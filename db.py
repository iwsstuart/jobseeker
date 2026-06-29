import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "jobseeker.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            careers_url     TEXT,
            ats             TEXT NOT NULL,
            ats_identifier  TEXT,
            active          INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
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
        );

        CREATE TABLE IF NOT EXISTS job_extractions (
            job_id            INTEGER PRIMARY KEY REFERENCES jobs(id),
            skills            TEXT,
            experience_level  TEXT,
            key_requirements  TEXT,
            extracted_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS match_results (
            job_id        INTEGER PRIMARY KEY REFERENCES jobs(id),
            is_match      INTEGER NOT NULL,
            reasoning     TEXT,
            notified_at   TEXT,
            evaluated_at  TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
