# TODO

## Known issues
- [ ] Duplicate job listings: some roles appear twice in match results (e.g. Sigma "Software Engineer - Compiler", Teads "Data Engineer - Finance Solutions Team", Teads "Senior Data Engineer - Big Data"). Likely duplicate postings in Greenhouse — investigate and consider deduplicating at the fetch or display level.

## Ops
- [ ] To inspect the DB after a GitHub Actions run: `gh run download --name jobseeker-db` pulls the latest artifact locally.

## Profile tuning (after more data)
- [ ] Consider tightening profile to exclude customer-facing roles (Solutions Engineer, Technical Support Manager) that are surfacing as borderline matches.
