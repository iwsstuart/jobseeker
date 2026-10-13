"""Title pre-filter for the Job Seeker pipeline (deterministic, no AI).

Logic: a title is excluded if it matches an exclusion keyword, UNLESS it also
matches the allowlist (a core-skill signal). The allowlist only matters when an
exclusion fires, so the returned reason records exactly what the allowlist saved.

NOTE: Excluding generic software / infra / IT engineering titles is a
deliberate, cost-driven tightening. profile.md treats these as *weaker*
matches, not exclusions -- this filter does not contradict the profile, it
trades recall on those roles for lower token spend. The allowlist is the
safety valve.
"""
import hashlib
import json
import re

# Prefix-boundary matching: keyword must start at a word boundary, but may
# continue ("recruiter" matches "recruiters", "sales assist" matches
# "sales assistant"). Plain substring matching was dropped so that, e.g.,
# "ios" can't match inside "studios".
EXCLUDE_KEYWORDS = [
    # Sales
    "account executive",
    "account manager",
    "business development",
    "sales development",
    "sales director",
    "sales assist",
    # Recruiting / HR
    "recruiter",
    "sourcer",
    "talent acquisition",
    "hr business partner",
    # Legal / Procurement
    "paralegal",
    "procurement",
    # Accounting
    "accountant",
    "accounts receivable",
    # Clinical (Headway-specific)
    "licensed",
    "medical director",
    "medical coding",
    "payer partnerships",
    "care partnerships",
    # Design
    "product designer",
    "graphic designer",
    # Customer success / admin
    "customer success",
    "office manager",
    # Marketing
    "content marketing",
    # Catch-all
    "summer school",
    "general application",
    "talent community",
    # --- Engineering: generic software / infra (deliberate tightening) ---
    "software engineer",
    "software developer",
    "engineering manager",
    "engineering director",
    "director of engineering",
    "head of engineering",
    "vp of engineering",
    "vp, engineering",
    "devops",
    "site reliability",
    "platform engineer",
    "infrastructure engineer",
    "cloud engineer",
    "security engineer",
    "systems engineer",
    "network engineer",
    "frontend",
    "front-end",
    "front end",
    "backend",
    "back-end",
    "back end",
    "full stack",
    "full-stack",
    "fullstack",
    "mobile engineer",
    "mobile developer",
    "qa engineer",
    "test engineer",
    "test automation",
    # --- Engineering: hardware / embedded ---
    "embedded",
    "firmware",
    "hardware",
    "mechanical engineer",
    "electrical engineer",
    # --- Customer-facing engineering / IT ---
    "solutions engineer",
    "sales engineer",
    "support engineer",
    "customer engineer",
    "technical support",
    "it systems",
    "it support",
    "help desk",
    "systems administrator",
    # Optional, much heavier: drops ANY "engineer" title unless allowlisted.
    # Would also drop e.g. "Forward Deployed Engineer" / "Founding Engineer"
    # at AI companies unless "AI" is in the title. Enable only if volume is
    # still too high after reviewing the filter audit log.
    # "engineer",
]

# Short tokens that need a boundary on BOTH sides to avoid false hits.
EXCLUDE_WORDS = ["sre", "ios", "android", "qa", "sdet"]

# Allowlist: a strong core-skill signal rescues an otherwise-excluded title.
# Whole-word matching so "ai" doesn't hit "retail" and "ml" doesn't hit "html".
ALLOW_TERMS = [
    "data",
    "analytics",
    "analytic",
    "analyst",
    "scientist",
    "science",
    "insights",
    "intelligence",      # business intelligence / artificial intelligence
    "bi",
    "ai",
    "ml",
    "llm",
    "genai",
    "generative",
    "nlp",
    "machine learning",
    "decision science",
    "geospatial",
    "gis",
    "postgis",
    "forecasting",
    "experimentation",
    "dbt",
    "sql",
    "python",
    "snowflake",
    "bigquery",
]

def build_classifier(exclude_keywords, exclude_words, allow_terms):
    """Compile a (title) -> ("keep" | "exclude", reason) classifier for a
    specific set of term lists. Lets callers reconstruct the classifier for
    any historical ruleset (e.g. one pulled from the filter_rulesets table),
    not just the live one.
    """
    exclude_re = re.compile(
        r"\b(?:" + "|".join(re.escape(k) for k in exclude_keywords) + r")",
        re.IGNORECASE,
    )
    exclude_word_re = re.compile(
        r"\b(?:" + "|".join(exclude_words) + r")\b", re.IGNORECASE
    )
    allow_re = re.compile(
        r"\b(?:" + "|".join(re.escape(t) for t in allow_terms) + r")\b",
        re.IGNORECASE,
    )

    def classify(title: str) -> tuple[str, str | None]:
        """Return ("keep" | "exclude", reason). Reason is None for a plain keep."""
        m = exclude_re.search(title) or exclude_word_re.search(title)
        if m is None:
            return "keep", None
        hit = m.group(0).lower()
        if a := allow_re.search(title):
            return "keep", f"rescued by '{a.group(0).lower()}' (would have matched '{hit}')"
        return "exclude", hit

    return classify


classify_title = build_classifier(EXCLUDE_KEYWORDS, EXCLUDE_WORDS, ALLOW_TERMS)


def ruleset_version(
    exclude_keywords=EXCLUDE_KEYWORDS, exclude_words=EXCLUDE_WORDS, allow_terms=ALLOW_TERMS
) -> str:
    """Short, automatic hash identifying a specific set of term lists --
    changes whenever the lists change, with no manual bumping required."""
    payload = json.dumps(
        {
            "exclude_keywords": exclude_keywords,
            "exclude_words": exclude_words,
            "allow_terms": allow_terms,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


RULESET_VERSION = ruleset_version()


def ensure_ruleset_recorded(conn):
    """Insert the current ruleset into filter_rulesets if not already present.
    Cheap, once-per-distinct-ruleset -- call once per run, not once per job."""
    from psycopg.types.json import Jsonb

    conn.execute(
        """INSERT INTO filter_rulesets (version, exclude_keywords, exclude_words, allow_terms, recorded_at)
           VALUES (%s, %s, %s, %s, NOW()::text)
           ON CONFLICT (version) DO NOTHING""",
        (RULESET_VERSION, Jsonb(EXCLUDE_KEYWORDS), Jsonb(EXCLUDE_WORDS), Jsonb(ALLOW_TERMS)),
    )
    conn.commit()


if __name__ == "__main__":
    cases = {
        # Cadence titles
        "Senior Software Engineer, Agentic AI": "keep",
        "Senior Software Engineer, Security Infrastructure": "exclude",
        "Software Engineer": "exclude",
        "Engineering Manager": "exclude",
        "Staff DevOps Engineer": "exclude",
        "Senior IT Systems Engineer": "exclude",
        "Staff IT Systems Engineer": "exclude",
        "Senior Platform Engineer, GTM Systems": "exclude",
        "People Operations, Data, and Technology Director": "keep",
        "Applied AI Engineer": "keep",
        "Senior Product Manager": "keep",
        "Strategic Finance Associate": "keep",
        # Allowlist rescues / edge cases
        "Data Engineer": "keep",
        "Analytics Engineer": "keep",
        "Data Engineering Manager": "keep",
        "Machine Learning Platform Engineer": "keep",
        "iOS Engineer": "exclude",
        "Sr. SRE": "exclude",
        "Studio Operations Lead": "keep",  # "ios" must not match inside "studios"
        "Senior Account Executive": "exclude",
        "Business Development, Data Partnerships": "keep",  # known global-rescue side effect
    }
    bad = 0
    for title, want in cases.items():
        got, reason = classify_title(title)
        flag = "ok " if got == want else "BAD"
        bad += got != want
        print(f"{flag} {title!r:62} -> {got:7} {reason or ''}")
    raise SystemExit(bad)
