# TODO

## Known issues
- [ ] Backfill Rippling job descriptions: `fetchers/rippling.py` was pulling the wrong description field (`description.company`, generic boilerplate, instead of `description.role`, the actual posting) — fixed in code, but `fetch_company()` only sets `raw_description` on *new* job rows; any Rippling job already in the DB from before this fix keeps the old, wrong text until re-fetched or backfilled. Check whether any Rippling companies (e.g. Wherobots, Inspiration Mobility, or the Rippling test entry from debugging the `/add-company` flow) actually have job rows yet — if so, decide whether to backfill (re-fetch descriptions for existing rows) and re-run extraction/matching for them, since those were derived from the wrong text too.
- [ ] Duplicate job listings: some roles appear twice in match results (e.g. Sigma "Software Engineer - Compiler", Teads "Data Engineer - Finance Solutions Team", Teads "Senior Data Engineer - Big Data"). Likely duplicate postings in Greenhouse — investigate and consider deduplicating at the fetch or display level.
- [ ] Fetch retry on transient errors: a single company's fetch can fail on a network blip (e.g. Harvey/Ashby hit `ConnectionResetError` on 2026-09-21) and `fetch_company()` just logs it and moves on — that company is silently skipped for the whole day with no retry. Add a small retry (a couple of attempts with backoff) around the fetcher call before giving up and logging the error.
- [ ] "No new jobs evaluated today" is ambiguous: `notify.py` sends this same message whether there genuinely were no new postings, or extraction/matching failed for every job (e.g. the 2026-09-21 Anthropic credit exhaustion, where 483 jobs were fetched but 0 were evaluated). Notify needs to distinguish "nothing new" from "processing failed" — e.g. have extract.py/match.py surface failure counts, and have notify.py report something like "N jobs fetched but 0 evaluated — check logs" instead of implying a quiet, uneventful day.

## Profile tuning (after more data)
- [ ] Consider tightening profile to exclude customer-facing roles (Solutions Engineer, Technical Support Manager) that are surfacing as borderline matches.

## Ideas
- [ ] Workflow for adding jobs found on LinkedIn: only add if the role can also be found on the company's own jobs page (i.e. it's a real, current posting, not stale/reposted). If the company isn't tracked yet, add the new company first.
