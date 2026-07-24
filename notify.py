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

    jobs = conn.execute("""
        SELECT j.id, j.title, j.url, c.name AS company, mr.reasoning
        FROM match_results mr
        JOIN jobs j ON j.id = mr.job_id
        JOIN companies c ON c.id = j.company_id
        WHERE mr.is_match = 1 AND mr.notified_at IS NULL
        ORDER BY c.name, j.title
    """).fetchall()

    if not jobs:
        print("No new matches to notify.")
        return

    message = format_digest(jobs)
    print(message)
    print()

    send_slack_message(message)

    ids = [job["id"] for job in jobs]
    conn.execute(
        f"UPDATE match_results SET notified_at = datetime('now') WHERE job_id IN ({','.join('?' * len(ids))})",
        ids,
    )
    conn.commit()
    conn.close()
    print(f"Notified: {len(jobs)} matches sent to Slack.")


if __name__ == "__main__":
    run_notify()
