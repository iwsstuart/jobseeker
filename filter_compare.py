"""Read-only tool for exploring the impact of title_filter.py's term lists
against real, accumulated job titles -- and for looking up what a specific
past ruleset version actually contained. Never writes to the database.

Usage:
    python filter_compare.py                          # summary of current rules vs all jobs
    python filter_compare.py --list keep               # dump every kept title
    python filter_compare.py --list exclude            # dump every excluded title
    python filter_compare.py --versions                # list all recorded ruleset versions
    python filter_compare.py --show-ruleset <version>   # print that version's term lists
    python filter_compare.py --diff <version>           # current rules vs a past version
"""
import sys
from collections import Counter

from db import get_connection
from title_filter import classify_title, build_classifier, RULESET_VERSION


def _fetch_jobs(conn):
    return conn.execute("SELECT id, title FROM jobs").fetchall()


def summary(conn):
    rows = _fetch_jobs(conn)
    exclude_reasons = Counter()
    rescue_reasons = Counter()
    examples = {}
    keep, exclude = 0, 0

    for job in rows:
        verdict, reason = classify_title(job["title"])
        if verdict == "exclude":
            exclude += 1
            exclude_reasons[reason] += 1
            examples.setdefault(("exclude", reason), job["title"])
        else:
            keep += 1
            if reason:
                rescue_reasons[reason] += 1
                examples.setdefault(("rescue", reason), job["title"])

    total = keep + exclude
    print(f"Ruleset version: {RULESET_VERSION}")
    print(f"Total jobs: {total}  |  keep: {keep} ({keep / total:.0%})  |  exclude: {exclude} ({exclude / total:.0%})\n")

    print("Excluded, by keyword:")
    for reason, count in exclude_reasons.most_common():
        print(f"  {count:4}  {reason!r:30} e.g. {examples[('exclude', reason)]!r}")

    print("\nRescued keeps, by allow-term:")
    for reason, count in rescue_reasons.most_common():
        print(f"  {count:4}  {reason}")


def list_titles(conn, which):
    if which not in ("keep", "exclude"):
        sys.exit(f"--list expects 'keep' or 'exclude', got {which!r}")
    rows = _fetch_jobs(conn)
    for job in rows:
        verdict, reason = classify_title(job["title"])
        if verdict == which:
            print(f"[{job['id']}] {job['title']!r}  {reason or ''}")


def list_versions(conn):
    rows = conn.execute(
        "SELECT version, recorded_at FROM filter_rulesets ORDER BY recorded_at"
    ).fetchall()
    if not rows:
        print("No ruleset versions recorded yet -- run filter.py or filter_rescue.py at least once.")
        return
    for r in rows:
        marker = " (current)" if r["version"] == RULESET_VERSION else ""
        print(f"{r['version']}  recorded {r['recorded_at']}{marker}")


def show_ruleset(conn, version):
    row = conn.execute(
        "SELECT exclude_keywords, exclude_words, allow_terms, recorded_at FROM filter_rulesets WHERE version = %s",
        (version,),
    ).fetchone()
    if not row:
        print(f"No recorded ruleset with version {version!r}. Run --versions to see what's available.")
        return
    print(f"Ruleset {version}  (recorded {row['recorded_at']})")
    print(f"\nEXCLUDE_KEYWORDS ({len(row['exclude_keywords'])}):")
    for k in row["exclude_keywords"]:
        print(f"  {k}")
    print(f"\nEXCLUDE_WORDS ({len(row['exclude_words'])}): {row['exclude_words']}")
    print(f"\nALLOW_TERMS ({len(row['allow_terms'])}): {row['allow_terms']}")


def diff_against(conn, version):
    row = conn.execute(
        "SELECT exclude_keywords, exclude_words, allow_terms FROM filter_rulesets WHERE version = %s",
        (version,),
    ).fetchone()
    if not row:
        print(f"No recorded ruleset with version {version!r}. Run --versions to see what's available.")
        return

    old_classify = build_classifier(row["exclude_keywords"], row["exclude_words"], row["allow_terms"])
    rows = _fetch_jobs(conn)

    flips_to_keep, flips_to_exclude = [], []
    unchanged = 0
    for job in rows:
        old_verdict, old_reason = old_classify(job["title"])
        new_verdict, new_reason = classify_title(job["title"])
        if old_verdict == new_verdict:
            unchanged += 1
        elif new_verdict == "keep":
            flips_to_keep.append((job, old_reason, new_reason))
        else:
            flips_to_exclude.append((job, old_reason, new_reason))

    print(f"Comparing current ({RULESET_VERSION}) against {version}\n")
    print(f"Unchanged: {unchanged}")

    print(f"\nFlipped exclude -> keep ({len(flips_to_keep)}):")
    for job, old_reason, new_reason in flips_to_keep:
        print(f"  [{job['id']}] {job['title']!r}  was: {old_reason!r}  now: {new_reason!r}")

    print(f"\nFlipped keep -> exclude ({len(flips_to_exclude)}):")
    for job, old_reason, new_reason in flips_to_exclude:
        print(f"  [{job['id']}] {job['title']!r}  was: {old_reason!r}  now: {new_reason!r}")


def main():
    conn = get_connection()
    args = sys.argv[1:]

    if not args:
        summary(conn)
    elif args[0] == "--list" and len(args) > 1:
        list_titles(conn, args[1])
    elif args[0] == "--versions":
        list_versions(conn)
    elif args[0] == "--show-ruleset" and len(args) > 1:
        show_ruleset(conn, args[1])
    elif args[0] == "--diff" and len(args) > 1:
        diff_against(conn, args[1])
    else:
        print(__doc__)

    conn.close()


if __name__ == "__main__":
    main()
