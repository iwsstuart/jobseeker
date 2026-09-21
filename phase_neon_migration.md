# Phase Brief — Migrate to Neon Postgres

## Purpose
Replace the current `actions/cache`-based SQLite persistence with a real,
always-available Postgres database on Neon. This removes the structural
fragility of using GitHub's dependency cache as a data store (eviction
risk, no durability guarantee, single-writer-only design — see prior
discussion) and is a deliberate prerequisite for the next phase: a live
service for adding companies on demand (e.g. from mobile, via Slack —
see "Coupling with the next phase" below), which requires a database
that's reachable outside the batch-cron execution window.

## Sequencing
This phase runs on its own, built and verified before the add-company
live service. The two are closely related but not combined — see
reasoning above. The add-company service is a separate, immediately
following phase, not scoped here.

## Explicitly out of scope for this phase
- **The add-company live service itself** (Slack-based or otherwise).
  This phase only prepares the database to support it later.
- **Any schema/data-model changes beyond what the Postgres migration
  itself requires** (type translation, JSONB, etc.). No new tables,
  columns, or logical changes — see "Data model" below.
- **ATS detection, custom-page tracking, match-result versioning.** All
  separately scoped or deferred elsewhere, unaffected by this migration.
- **Any UI change.** The existing CLI keeps working exactly as before —
  it just points at Neon instead of a local SQLite file.

## Coupling with the next phase (why this matters here)
The add-company service will need to open database connections from a
short-lived, possibly-concurrent context (a webhook handler responding
to a Slack request), which is a different connection pattern than a
single long-running cron job. Neon's pooled connection string (via its
built-in PgBouncer-compatible pooler) is designed for exactly this. To
avoid reconfiguring this later, **this migration should adopt the pooled
connection string as the standard from day one** — even though the cron
job alone doesn't strictly need pooling yet. This is a small, free
decision now that saves a rework step later.

## Data model
No logical schema changes — same tables, same columns, same
relationships. What changes is physical representation:
- `active` (and any other boolean columns) move from SQLite's implicit
  0/1 integers to real Postgres `BOOLEAN`.
- `job_extractions.skills` and `key_requirements` move from JSON-as-text
  to native `JSONB` — a genuine upgrade (queryable), not just a format
  change, but requires updating how these columns are declared and how
  the extraction step writes to them.
- Any `INSERT OR IGNORE` / `INSERT OR REPLACE` dedup logic (used for
  `external_id` deduplication in the fetch step) needs rewriting as
  Postgres `INSERT ... ON CONFLICT (external_id) DO UPDATE/NOTHING`.
  This is the one piece of business logic most likely to have a subtle
  behavioral difference if not translated carefully — verify dedup
  behavior explicitly during testing, not just schema correctness.

## Migration approach
One-time cutover, not a dual-running migration — there's no need to run
old and new systems in parallel. Export the most recent SQLite snapshot
(from the current `actions/cache`), transform per the above, load into a
new Neon database, switch the pipeline's connection code over, and retire
the `actions/cache` save/restore steps entirely.

## Build order
1. Create the Neon project. Use the pooled connection string as the
   connection method from the start (see "Coupling" above).
2. Translate the schema: DDL rewritten for Postgres types (real
   booleans, `JSONB` columns, standard `SERIAL`/`IDENTITY` primary keys).
3. One-time data migration: export the current SQLite file (from the
   latest `actions/cache` entry), transform, load into Neon.
4. Update pipeline code: replace `sqlite3` with `psycopg`, rewrite any
   dialect-specific SQL (upsert/dedup logic especially), pull the
   connection string from a GitHub Actions secret.
5. Remove the `actions/cache` restore/save steps from the workflow —
   the pipeline now connects directly to Neon at both start and end.
6. Verify correctness without waiting on real time. Two separate checks,
   both fast:
   - **Pipeline runs correctly against Neon**: trigger the workflow
     manually via `workflow_dispatch` as many times as needed, rather
     than waiting for the daily schedule.
   - **Dedup and `status`/`closed` transition logic is correct**: don't
     wait for real ATS postings to change. Use a Neon dev branch
     (isolated from production data) and run the fetch/dedup step twice
     against two synthetic fixture batches you construct yourself — e.g.
     batch 1 has jobs A/B/C, batch 2 has A/B/D (C missing, D new).
     Confirm `external_id` dedup doesn't create duplicates on the second
     run, and that C flips to `status = closed` while D is correctly
     inserted as new. This is both faster and more reliable than waiting
     on real postings to change organically.
7. (Optional but recommended, cheap to set up now) Create a Neon dev
   branch for local development/testing going forward, replacing
   whatever ad hoc local-SQLite-file workflow existed before.

## Notes for later (not this phase, but relevant context)
- The add-company live service (next phase) will connect to this same
  Neon database via the pooled connection string already established
  here. No further database changes are anticipated when that phase
  starts — it's a new client connecting to an already-correct setup.
- Worth considering a lightweight heartbeat/dead-man's-switch monitor
  (e.g. healthchecks.io-style) as a small follow-up, now that
  `actions/cache` — which incidentally left an inspectable trail of
  cached snapshots — is gone. This isn't required for this phase, but is
  a natural complement to it: it catches "the pipeline didn't run at
  all," which ordinary error reporting doesn't.
