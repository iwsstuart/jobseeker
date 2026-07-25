# TODO

## Known issues
- [ ] Duplicate job listings: some roles appear twice in match results (e.g. Sigma "Software Engineer - Compiler", Teads "Data Engineer - Finance Solutions Team", Teads "Senior Data Engineer - Big Data"). Likely duplicate postings in Greenhouse — investigate and consider deduplicating at the fetch or display level.

## Ops
- [ ] To inspect the DB after a GitHub Actions run: the DB now persists via `actions/cache` (key `jobseeker-db-<run_id>`), not an artifact, so `gh run download` no longer works. Use the `gh actions-cache` extension (`gh extension install actions/gh-actions-cache`) to list/download the cache instead.

## Profile tuning (after more data)
- [ ] Consider tightening profile to exclude customer-facing roles (Solutions Engineer, Technical Support Manager) that are surfacing as borderline matches.

## Ideas
- [ ] Workflow for adding jobs found on LinkedIn: only add if the role can also be found on the company's own jobs page (i.e. it's a real, current posting, not stale/reposted). If the company isn't tracked yet, add the new company first.
