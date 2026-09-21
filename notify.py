import json
import os
import requests
from db import get_connection

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def send_slack_message(text: str):
    if not SLACK_WEBHOOK_URL:
        raise SystemExit("SLACK_WEBHOOK_URL environment variable not set.")
    resp = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
    resp.raise_for_status()


def format_digest(jobs: list[dict]) -> str:
    lines = [f"*{len(jobs)} new job match{'es' if len(jobs) != 1 else ''}*\n"]
    for job in jobs:
        lines.append(f"• *{job['title']}* @ {job['company']}")
        lines.append(f"  {job['url']}")
        first_sentence = job["reasoning"].split(".")[0] + "."
        lines.append(f"  _{first_sentence}_")
        lines.append("")
    return "\n".join(lines).strip()


def run_notify():
    conn = get_connection()

    matches = conn.execute("""
        SELECT j.id, j.title, j.url, c.name AS company, mr.reasoning
        FROM match_results mr
        JOIN jobs j ON j.id = mr.job_id
        JOIN companies c ON c.id = j.company_id
        WHERE mr.is_match AND mr.notified_at IS NULL
        ORDER BY c.name, j.title
    """).fetchall()

    if matches:
        message = format_digest(matches)
    else:
        total_evaluated = conn.execute(
            "SELECT COUNT(*) FROM match_results WHERE evaluated_at::timestamptz::date = CURRENT_DATE"
        ).fetchone()["count"]
        if total_evaluated:
            message = f"No matches today — {total_evaluated} new job{'s' if total_evaluated != 1 else ''} evaluated."
        else:
            message = "No new jobs evaluated today."

    print(message)
    print()

    send_slack_message(message)

    if matches:
        ids = [job["id"] for job in matches]
        conn.execute(
            f"UPDATE match_results SET notified_at = NOW()::text WHERE job_id IN ({','.join(['%s'] * len(ids))})",
            ids,
        )
        conn.commit()
    conn.close()
    print(f"Notified: {len(matches)} matches sent to Slack.")


if __name__ == "__main__":
    run_notify()
