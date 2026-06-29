# Job Seeker Tool — Project Brief

## Purpose
A personal tool to track interesting job openings at a defined list of
companies, extract structured signal from postings, match them against a
candidate profile, and notify via email. Built to replace manual checking
of individual company job boards, which doesn't scale past a handful of
companies.

## Constraints
- Builder has prior Python/SQL experience (analytics background), no
  strong opinion on architecture beyond that
- ~2 hours/day, target of a working deployed v1 within ~2 weeks
- Bare-bones interface is fine — no UI in v1

## Stack
- **Language**: Python
- **Storage**: SQLite
- **Intelligence layer**: Claude API (extraction + matching)
- **Notifications**: Email (smtplib or similar)
- **Scheduling/hosting**: TBD at deployment step — likely Railway, Render,
  or a GitHub Actions scheduled workflow (cron). Decide at that stage, not
  before — don't let this block earlier steps.

## Explicitly deferred (not v1)
- On-demand querying (outside the schedule)
- Any UI (web, chat-based, etc.)
- Trend/synthesis analysis across accumulated job data (v2 — see below)
- Node.js/Next.js — not used anywhere in this project
- Comparative "what changed since last week" analysis (v2)

## Company audit (input data)
A CSV of target companies has been audited for ATS platform:

| ATS | Companies | Notes |
|---|---|---|
| Greenhouse | Teads, Overstory, Carbon Direct, Sigma | Clean public API |
| Ashby | Zapier, Headway | Clean public API |
| Rippling | Wherobots, Inspiration Mobility | Unconfirmed API access — investigate in second pass |
| Pinpoint | Carto | Unconfirmed API access — investigate in second pass |
| Unknown | Electricity Maps, Chargetrip | No ATS identified — needs manual investigation |

**Build priority**: Greenhouse and Ashby fetchers first (6 of 11 companies,
validates the full pipeline end-to-end). Rippling, Pinpoint, and the two
unknowns are a second pass, not a blocker for v1.

## Data model

**`companies`**
- id (PK)
- name
- careers_url
- ats (`greenhouse` / `ashby` / `rippling` / `pinpoint` / `unknown`)
- ats_identifier (board token/slug used in API calls)
- active (boolean)

**`jobs`**
- id (PK)
- company_id (FK)
- external_id (ATS-native ID — used for dedup)
- title
- url
- raw_description
- first_seen_at
- last_seen_at
- status (`open` / `closed`) — tracks whether still live on company site
- processing_status (`new` / `filtered_out` / `evaluated`) — tracks
  pipeline progress, independent of `status`

**`job_extractions`**
- job_id (FK)
- skills (JSON list)
- experience_level
- key_requirements (JSON list)
- extracted_at
- Runs on every evaluated job, not just matches — this is intentional,
  it's what enables v2 trend analysis later without re-fetching.

**`match_results`**
- job_id (FK)
- is_match (boolean)
- reasoning (text — Claude's explanation, kept even for non-matches)
- notified_at (nullable — null means not yet notified)
- evaluated_at
- Non-matches are stored deliberately, for dedup, auditability, and
  profile-tuning purposes. This is not a bug, don't "optimize" it away.

**Profile** — lives as a separate markdown file (`profile.md`), not a DB
table. Read into the matching prompt directly. See attached.

## Pipeline logic
1. **Fetch**: pull jobs per company (Greenhouse/Ashby API calls first).
   Dedup on `external_id`. Update `last_seen_at`; flip `status` to
   `closed` for jobs no longer present in a fetch.
2. **Title pre-filter**: deterministic keyword filter (not Claude) to
   exclude obvious non-matches (Sales, Recruiter, HR titles, etc.).
   Sets `processing_status = filtered_out`. Keyword list TBD — draft this
   during implementation, not before.
3. **Extraction**: Claude call per job with `processing_status = new`,
   populates `job_extractions` (skills, experience level, requirements).
4. **Matching**: Claude call using `profile.md` + extracted data, populates
   `match_results`. Flips `processing_status` to `evaluated`.
5. **Notification**: email for any `match_results` row where
   `is_match = true` and `notified_at IS NULL`. Sets `notified_at` after
   sending.
6. **Scheduling**: wrap as a script, deploy on a daily cron. Last step —
   get the full pipeline working and trustworthy locally first.

## Build order
1. `companies` table + Greenhouse/Ashby fetchers → raw jobs land in `jobs`,
   verified dedup on repeated runs
2. Title pre-filter
3. Extraction step (Claude call → `job_extractions`)
4. Matching step (Claude call + `profile.md` → `match_results`)
5. Email notification
6. Scheduling/deployment (Railway/Render/GitHub Actions — decide at this step)

Second pass (after v1 is working end-to-end):
- Rippling/Pinpoint fetchers
- Investigate Electricity Maps and Chargetrip
- v2: trend/synthesis analysis across `job_extractions` over time

## Key design decisions worth preserving context on
- `jobs` and `job_extractions` are deliberately separate: raw fetch vs.
  Claude-derived interpretation, so a bad extraction prompt never requires
  re-scraping.
- `status` and `processing_status` are deliberately separate fields on
  `jobs`: one tracks live/closed on the company site, the other tracks
  pipeline progress. They change for different reasons and should not be
  conflated.
- Matching profile is intentionally generous for v1 (broad domain, broad
  seniority, broad title matching) — the `reasoning` field on
  `match_results` is what makes this safe, since nothing is silently
  filtered without an explanation. Expect to tighten the profile after a
  few weeks of real output.
- AI is used for extraction and matching (fuzzy, judgment-based tasks),
  not for the pre-filter (deterministic, cheap, should stay a keyword list).
