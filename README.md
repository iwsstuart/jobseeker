# jobseeker

Personal tool that monitors job boards at target companies, extracts structured signal from postings using Claude, matches them against a candidate profile, and sends a Slack digest of new matches.

## Pipeline

```
fetch → filter → extract → match → notify
```

1. **fetch** — pulls open jobs from Greenhouse and Ashby APIs, deduplicates by external ID
2. **filter** — keyword-based title pre-filter to exclude obvious non-matches (sales, recruiting, etc.)
3. **extract** — Claude (Haiku) extracts skills, experience level, and key requirements from each job description
4. **match** — Claude evaluates each extracted job against `profile_prompt.md`, storing a match decision and reasoning
5. **notify** — sends a Slack digest of new matches via incoming webhook

Runs daily at 6am CET via GitHub Actions. The SQLite database is persisted between runs as a GitHub Actions artifact.

## Setup

### Requirements

- Python 3.11+
- `pip install -r requirements.txt`

### Environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key for extraction and matching |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL for notifications |

### First run

```bash
python seed.py          # populate companies table
python fetch.py         # fetch jobs
python filter.py        # apply title pre-filter
ANTHROPIC_API_KEY=... python extract.py   # extract structured data
ANTHROPIC_API_KEY=... python match.py     # match against profile
SLACK_WEBHOOK_URL=... python notify.py    # send Slack digest
```

Or run the full pipeline in one step:

```bash
ANTHROPIC_API_KEY=... SLACK_WEBHOOK_URL=... python run.py
```

## Supported ATS platforms

- Greenhouse
- Ashby

## Customisation

- **Profile** — edit `profile_prompt.md` to update the candidate profile used for matching
- **Companies** — add rows to `seed.py` and re-run it to add new target companies
- **Title filter** — edit `EXCLUDE_KEYWORDS` in `filter.py`
