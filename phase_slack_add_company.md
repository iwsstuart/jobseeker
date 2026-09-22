# Phase Brief — Slack "Add Company" Service

## Purpose
Give the existing company-onboarding logic (name/URL/platform/slug entry
→ resolver verification → confirm → write) a Slack-based interface, so
new companies can be added from mobile or desktop without SSH-ing in or
running the CLI locally. This is an interface change, not a redesign —
the trust model, resolver logic, and verification behavior established in
`phase_company_onboarding.md` (and extended to more platforms in
`phase_additional_platforms.md`) carry over unchanged. This phase builds
the frontend for logic that already exists.

Runs after the completed Neon migration (`phase_neon_migration.md`),
which is exactly what makes this possible — a live webhook handler can
now connect to the same database the cron job uses, via the pooled
connection string already set up for this purpose.

## Explicitly out of scope for this phase
- **ATS auto-detection.** Separate phase (`phase_ats_detection.md`), not
  built here — the user still identifies platform/slug directly.
- **Any change to the resolver's verification logic itself** (the
  success / zero-results / hard-failure classification). This phase
  reuses it as-is, only changes how the user interacts with it.
- **Custom company-website tracking, match-result versioning.**
  Unrelated to this phase.
- **General company editing beyond what already existed**: adding new
  companies and toggling `active`, same scope as the original onboarding
  CLI — not a general company-record editor.

## What carries over unchanged from the onboarding CLI phase
- Only a slug/platform the user has directly identified is accepted — no
  AI-assisted or inferred lookup.
- Resolver verification (live API check) runs before any write.
- Zero-results and hard-failure are distinct, explicitly labeled outcomes
  — not collapsed into one generic error.
- Nothing is written to the database without explicit user confirmation.

## Design decisions specific to Slack

### Slash command with a modal, not free-text parsing
A slash command (e.g. `/add-company`) should open a Slack modal (Block
Kit form) rather than requiring the user to type all fields as a single
space-separated string. This avoids parsing ambiguity, gives clear field
labels, and is meaningfully easier to use on mobile than typing a
precisely-formatted command. Fields: company name, careers URL, ATS
platform (dropdown, populated from currently-supported platforms —
Greenhouse/Ashby/Lever/Rippling/Pinpoint), slug.

### Slack's 3-second ack requirement needs an async pattern
Slack requires an initial response within 3 seconds of a modal submission
or interaction; the resolver's live API call to the ATS may take longer.
Pattern: acknowledge the submission immediately (e.g. "Checking that
slug..."), run the resolver check asynchronously, then post the result
back via Slack's `response_url` (or a threaded reply) once it completes.
This is a real implementation detail, not a minor one — a resolver call
that blocks past 3 seconds without this pattern will cause Slack to
report a failure to the user even if the check eventually succeeds.

### Confirmation via buttons, not typed replies
Once the resolver returns a result, post a message with the job count and
a few sample titles, plus interactive "Confirm" / "Reject" buttons
(Slack's Block Kit interactive components) rather than asking the user to
type "yes"/"no". More reliable than free-text parsing, and easier on
mobile. This is the direct Slack equivalent of the CLI's existing
confirm-before-write step.

### Active toggle
A second command (or a menu option within the same command) lists
existing companies via a select menu and confirms the flip, mirroring the
CLI's toggle flow from the onboarding phase. No resolver involvement,
same as before — this only changes the `active` flag on an
already-verified record.

## Security
- **Verify Slack request signatures** on every incoming request, using
  the app's signing secret, before processing anything — this confirms
  requests genuinely originate from Slack and haven't been spoofed.
- **Restrict who can trigger writes.** Even in a small/private workspace,
  explicitly check the invoking Slack user ID against an allowed list
  (likely just you) before running the resolver or writing anything —
  this is now a write path into production data, a higher bar than the
  read-only notification flow that existed before.
- Signing secret and the Neon connection string are both credentials —
  store them in the hosting platform's secret manager, never in code or
  committed config, consistent with `CLAUDE.md`'s git-hygiene rule.

## Hosting
A small serverless function (e.g. AWS Lambda + API Gateway, or Google
Cloud Run) is the natural fit: low, occasional traffic, no need for an
always-on server, minimal cost at this scale. Exact platform choice is an
implementation-time decision, not something to over-plan here — the
requirements are just: reachable over HTTPS, can hold the Slack signing
secret and Neon connection string as secrets, can make outbound calls to
ATS APIs and to Neon.

## Data model
No changes. Same `companies` table, same fields, same Neon database
already in place — this phase adds a new client connecting to it, not a
new schema.

## Build order
1. Create the Slack app: register `/add-company` (and the toggle
   command/flow), configure the modal form, obtain the signing secret.
2. Stand up the webhook handler on the chosen hosting platform; wire up
   signature verification and the allowed-user check first, before any
   business logic — reject everything else before it reaches the
   resolver.
3. Port the existing resolver-calling logic from the CLI into the
   handler, unchanged in behavior. Implement the async ack →
   `response_url` follow-up pattern for the verification step.
4. Implement the confirm/reject button flow and the write-on-confirm
   step, connecting to Neon via the pooled connection string.
5. Implement the active-toggle command/flow.
6. Manual verification: run through a new-company add (success,
   zero-results, hard-failure) and a toggle, from both desktop and mobile
   Slack, confirming behavior matches the CLI's original guarantees —
   nothing written without confirmation, in any case.
7. Decide whether to retire the local CLI or keep it as a fallback —
   likely keep it, since it's already built and costs nothing to leave
   in place as a backup entry point.
