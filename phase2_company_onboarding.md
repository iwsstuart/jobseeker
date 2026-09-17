# Phase Brief — Company Onboarding

## Purpose
Replace manual editing of the database seed file with a CLI-driven entry
process, plus a resolver that verifies the ATS slug against the live API
before anything is written to the database. Standing engineering
principles live in `CLAUDE.md`; this doc covers only what's specific to
this feature. (Match result versioning is a separate future phase — see
`phase2_matching_versioning.md` — and is not part of this brief.)

## Explicitly out of scope for this phase
- Match result / profile / schema versioning (separate phase).
- Any review or comparison UI.
- Rippling, Pinpoint, or unidentified-ATS support. This phase covers
  Greenhouse and Ashby only, matching the existing fetcher scope.
- AI-assisted slug/platform lookup for companies the user can't directly
  identify (see "Fallback path" note below — deferred, not this phase).
- General company-record editing (renaming, changing careers_url, etc.)
  beyond the `active` toggle. This phase is: add new companies, and
  toggle `active` on existing ones. Anything else is still a manual DB
  edit for now.

## Primary flow

### Adding a new company
1. User runs the CLI and enters: company name, careers URL, ATS platform,
   and ATS slug. In practice, platform and slug are typically observed
   together when the user looks at the careers page URL or page source,
   so requiring both up front is not extra burden over requiring one.
2. Resolver takes the entered slug and platform, hits the real ATS API
   endpoint (Greenhouse or Ashby), and checks the response.
3. On a clean success (valid response, one or more jobs returned): show
   the user a confirmation summary — job count and a few sample titles —
   and ask them to confirm before writing to the database.
4. On confirmation, write the new company record (name, careers_url, ats,
   ats_identifier, active) to the database. `active` defaults to `true`.

### Toggling `active` on an existing company
1. User runs the CLI in "toggle" mode (or a separate command), selects an
   existing company (by name or from a listed menu), and confirms the
   flip (active → inactive or vice versa).
2. No resolver check needed here — this only changes the `active` flag on
   an already-verified record, not the slug or platform.
3. Write the updated `active` value. Confirm change on screen (e.g. "Acme
   Co is now inactive — will be skipped by future fetches").

## Handling non-clean results
Two distinct failure signals, handled differently — do not collapse them
into one generic error:

- **Zero results** (API call succeeds, empty job list): ambiguous — could
  be a correct slug for a company not currently hiring, or a subtly wrong
  slug. Do not auto-generate candidate slugs or guess. Surface plainly:
  "slug `X` returned 0 jobs — please confirm this is correct," and let
  the user re-check the source page or re-enter. No automated fallback
  logic for this case.
- **Hard failure** (404, malformed response, endpoint doesn't exist):
  stronger signal the slug itself is wrong. Distinct message ("slug not
  found — check for typos"), prompting the user to re-check the URL and
  re-enter. Still no automated candidate-guessing here either — this is a
  human-resolvable problem in both cases, not one that needs inference
  machinery.

## No fallback lookup in this phase
Only slugs the user has identified directly are accepted. The assumption
is that the user encountered the company organically (e.g. browsing its
careers page) and can see the ATS platform and slug in the URL or page
source themselves — and can therefore verify the resolver's result
against what they're already looking at. There is no "I don't know the
slug" path in this phase; if the user can't identify the platform/slug
directly, onboarding that company is out of scope for now. AI-assisted
lookup for unidentified companies may be revisited in a later phase, but
deliberately excluded here to keep the primary flow's trust model simple:
every value written to the database traces back to something the user
personally observed and confirmed, not something inferred.

## Data written
No schema changes required — this phase populates and updates the
existing `companies` table (id, name, careers_url, ats, ats_identifier,
active) via the CLI instead of manual seed-file edits.

## Build order
1. CLI prompt script: collect name, careers_url, ats, ats_identifier from
   the user for new companies. No resolver yet — just structured input
   replacing the manual dict-editing.
2. Resolver: given platform + slug, call the live Greenhouse or Ashby API
   and classify the result (success / zero-results / hard-failure).
3. Wire resolver into the new-company CLI flow: run verification after
   entry, show the appropriate confirmation or error message per the
   three outcomes above, only write on explicit user confirmation.
4. Active-toggle flow: list/select an existing company, confirm, flip
   `active`. Independent of the resolver — can be built in parallel with
   or after steps 1–3.
5. Manual verification: run through all three new-company outcome paths
   (clean success, zero-results, hard-failure) and the toggle flow,
   confirm nothing is written without explicit confirmation in any case.

## Open questions to resolve during implementation
- Whether the CLI should support batch entry (multiple companies in one
  session) or strictly one-at-a-time — start with one-at-a-time, expand
  only if it proves annoying in practice.
- Whether "toggle mode" is a separate CLI command/entry point or a menu
  option within the same script as new-company entry — implementation
  detail, decide when building.
