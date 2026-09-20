# CLAUDE.md — Operating Principles for Job Seeker Tool

This file holds standing rules for how this codebase should be built and
extended. It does not track specific build steps or feature plans — those
live in phase-specific brief docs (e.g. `job_seeker_brief.md`,
`phase2_*.md`). If you find yourself writing "and then do X" here, it
probably belongs in a phase brief instead.

## Core design philosophy

- **Deterministic checks over inference, wherever possible.** Prefer a
  keyword filter, a live API call, or a schema constraint over an LLM
  guess, whenever the correct answer can be verified mechanically. AI is
  for genuinely fuzzy, judgment-based tasks (extraction, matching) — not
  for things that can be checked directly (e.g. resolving an ATS slug by
  testing it against the real API, not by guessing from a company name).
- **Human review before any write that can't be cheaply verified.**
  Anything AI-assisted or inferred (company lookups, slug candidates,
  profile changes) gets confirmed by the user before landing in the
  database. Automated writes are reserved for outputs of deterministic
  checks.
- **Silent failure is the primary risk to design against.** This tool
  runs unattended on a schedule — there's no one watching it fail in real
  time. Every integration point (ATS fetch, Claude call, notification
  send) should fail loudly (exception, log, flagged row) rather than
  quietly returning empty/wrong results. Zero-result and hard-failure
  cases should be distinguished, not collapsed into one silent no-op.
- **Tool use over prompt-based JSON extraction.** Any Claude call whose
  output needs to be parsed downstream should use tool calls for
  schema-level guarantees, not "please respond in JSON" prompting. This
  matters especially because the pipeline runs unattended — there's no
  human in the loop to catch a malformed response.
- **Decouple raw data from derived interpretation.** Store what was
  fetched separately from what Claude concluded about it (e.g. `jobs` vs
  `job_extractions`). This means a bad prompt or schema never requires
  re-fetching source data, only re-running the interpretation step.
- **Keep fields that change for different reasons separate**, even if
  they seem related (e.g. `status` vs `processing_status` on `jobs`).
  Don't conflate them for schema convenience.

## Working style

- **Use plan mode when the brief leaves something genuinely open** —
  an unresolved design question, a first-time integration with a new API,
  or logic with edge cases not already spelled out. Skip it when a task
  is a direct, unambiguous implementation of something already fully
  specified in a brief — plan mode there mostly just restates the spec
  back to you.
- **Write decisions to files, not just chat history**, given
  auto-compaction risk — design rationale and what changed and why
  belong in the relevant doc, not left to be reconstructed later.
- **Ground technical recommendations in current documentation**,
  especially for version-sensitive APIs, rather than relying on memory.
- **Explain the "why," not just the recommendation**, when proposing a
  technical approach.

## Stack conventions

- **Language/DB:** Python, SQLite. No Node.js/Next.js.
- **ATS integrations:** Greenhouse, Ashby, Lever, Rippling, and Pinpoint
  are all first-class (`fetch.py`'s `FETCHERS` dict). Unidentified
  platforms (no confirmed API) are still second-pass — don't let them
  block primary-path features.
- **Notifications:** Slack.
- **AI usage:** Anthropic/Claude API, with a spend cap given unattended
  usage. Use tool calls for structured output (see above).
- **Git hygiene:** `.gitignore` and `.env` discipline — never commit
  secrets or local config.

## Profile & matching notes

- `profile.md` is intentionally broad/generous for v1 — do not "fix"
  matching precision by silently tightening the profile without
  discussion. Non-matches are stored with reasoning specifically so
  matching quality can be audited and tuned deliberately.
- The matching *tool schema* (in `match.py`) and the *profile content*
  (`profile.md`) are separate tuning levers. A schema that only supports
  a boolean `is_match` can produce noisy results even with a well-written
  profile — check whether an issue is a schema granularity problem before
  editing profile prose to compensate.

## Explicit non-goals (standing, not phase-specific)

- No always-on chat/web UI — bare-bones interfaces only.
- No comparative "what changed since last week" analysis — that's
  deferred trend/synthesis work (v2).
