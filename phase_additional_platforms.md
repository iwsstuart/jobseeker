# Phase Brief — Additional ATS Platforms (Lever, Rippling, Pinpoint)

## Purpose
Extend the existing fetcher pattern (currently Greenhouse and Ashby) to
Lever, Rippling, and Pinpoint, and generalize the company onboarding
CLI/resolver (built in the prior phase) to support all three as options.
Lever is added for general coverage — no specific company on the current
list requires it yet, but it's the same clean, public, no-auth API tier
as Greenhouse/Ashby, so it's cheap to add and broadens what companies can
be onboarded going forward. Rippling and Pinpoint unblock tracking for
companies already identified in the original audit but deferred as
"second pass": Wherobots, Inspiration Mobility (Rippling) and Carto
(Pinpoint).

A separate, later phase will add ATS auto-detection from a careers URL
(see `phase_ats_detection.md`) — not part of this brief. This phase adds
platform support; detection comes after, once there's more than
Greenhouse/Ashby worth detecting for.

Sequencing note: this phase runs next, followed by the detection phase.
Match-result versioning is pushed out indefinitely. Custom
company-website tracking (companies with no ATS at all — Electricity
Maps, Chargetrip per the original audit) remains a separate, later phase
— see "Out of scope" below.

## Explicitly out of scope for this phase
- **ATS auto-detection from a careers URL.** Scoped separately as the
  next phase after this one — this phase still relies on the user
  identifying the platform and slug directly, per the onboarding phase's
  trust model.
- **Custom company-website tracking.** Different problem entirely (no
  structured API, needs page scraping/parsing) — a separate phase with
  its own design pass, not an extension of this one.
- **Investigating Electricity Maps or Chargetrip.** These have no
  identified ATS per the original audit. Whether they turn out to be a
  yet-unconfirmed ATS platform or genuinely need custom-page tracking is
  an open question for whenever that's picked up — not resolved here.
- **Match-result versioning.** Scoped previously
  (`phase2_matching_versioning.md`), pushed out indefinitely — not part
  of this brief.

## Lever: no access investigation needed
Unlike Rippling and Pinpoint, Lever's public postings API is documented
and confirmed: `GET https://api.lever.co/v0/postings/{slug}?mode=json`,
no authentication required, same shape of guarantee as Greenhouse and
Ashby. No prerequisite investigation step — go straight to building the
fetcher and resolver support.

## Rippling/Pinpoint prerequisite: confirm API access before building fetchers
The original audit flagged both as "unconfirmed API access — investigate
in second pass." That investigation is now the first step for these two
platforms specifically, not an assumption. Specifically confirm, per
platform:
- Does a public, unauthenticated job-board API/endpoint exist (as with
  Greenhouse and Ashby), or does access require an API key/auth?
- What does a successful response look like, and what does a
  zero-results / not-found response look like? (Needed to extend the
  resolver's success / zero-results / hard-failure classification, which
  was built against Greenhouse/Ashby response shapes and may not
  generalize automatically.)

**If either platform turns out to require authenticated access**, that's
a meaningful scope change worth flagging before building: it would mean
storing API keys per platform (`.env`, per `CLAUDE.md` git-hygiene rules)
and likely per-company or per-org credentials rather than a single public
endpoint pattern. Confirm this before committing to the build order below
— if true, treat it as a design checkpoint, not something to build past.

## Fetcher scope
Same responsibilities as the existing Greenhouse/Ashby fetchers, per
`job_seeker_brief.md`'s pipeline logic: pull jobs per company, dedup on
`external_id`, update `last_seen_at`, flip `status` to `closed` for jobs
no longer present in a fetch. `ats` already anticipates `rippling` and
`pinpoint` as values in the current schema/enum; `lever` will need to be
added as a new valid value alongside them — a small, low-risk schema/enum
change, not a structural one.

## Onboarding CLI/resolver generalization
The onboarding flow built in the prior phase (company entry, resolver
verification against the live API, zero-results/hard-failure handling)
was built against Greenhouse/Ashby specifically. Generalize it to:
- Accept `lever`, `rippling`, and `pinpoint` as valid platform selections.
- Route resolver verification to the correct per-platform endpoint and
  response-shape logic (see prerequisite above).
- Preserve the existing trust model unchanged: only slugs/identifiers the
  user has directly observed are accepted, same zero-results vs.
  hard-failure distinction, same confirm-before-write behavior.

## Build order
1. Build Lever fetcher, following the existing fetcher interface — no
   investigation step needed, API is already documented.
2. Add `lever` to the onboarding CLI/resolver as a valid platform;
   resolver verification against Lever's endpoint.
3. Confirm Rippling API access and response shape (success /
   zero-results / hard-failure cases).
4. Confirm Pinpoint API access and response shape.
5. Build Rippling fetcher, following the existing fetcher interface.
6. Build Pinpoint fetcher, same.
7. Add `rippling` and `pinpoint` to the onboarding CLI/resolver, same
   pattern as Lever.
8. Onboard the three known target companies (Wherobots, Inspiration
   Mobility, Carto) through the generalized CLI, confirming each resolves
   and returns expected job data.
9. Manual verification: confirm dedup and `status`/`closed` transitions
   work correctly for all three new fetchers on a second run, same as was
   verified for Greenhouse/Ashby originally.

## Follow-up (not blocking, but don't forget)
- Once shipped, the "ATS integrations" line in `CLAUDE.md` (currently:
  "Greenhouse and Ashby are primary... Rippling, Pinpoint... second-pass")
  is stale and should be updated to reflect that all four are now
  first-class.
