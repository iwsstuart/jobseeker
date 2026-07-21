import json
import os
from html.parser import HTMLParser

import anthropic

from db import get_connection

MODEL = "claude-haiku-4-5-20251001"

TOOL = {
    "name": "extract_job_info",
    "description": "Extract structured information from a job posting.",
    "input_schema": {
        "type": "object",
        "properties": {
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Technical skills, tools, languages, platforms, and frameworks mentioned. "
                    "Also include soft skills that are explicitly emphasized as central to the role "
                    "(e.g. cross-functional collaboration, mentorship, stakeholder alignment) — "
                    "not generic boilerplate like 'strong communicator'."
                ),
            },
            "experience_level": {
                "type": "string",
                "enum": ["junior", "mid", "senior", "staff", "principal", "manager", "executive", "unknown"],
                "description": "Seniority level of the role.",
            },
            "key_requirements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3 to 8 key requirements or responsibilities as short plain-English phrases.",
            },
        },
        "required": ["skills", "experience_level", "key_requirements"],
    },
}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return " ".join(self._parts)


def strip_html(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html or "")
    return parser.get_text().strip()


def extract_job(client: anthropic.Anthropic, job: dict) -> dict | None:
    description = strip_html(job["raw_description"])
    if not description:
        return None

    prompt = f"Job title: {job['title']}\n\n{description}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "extract_job_info"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_job_info":
            return block.input

    return None


def run_extraction():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY environment variable not set.")

    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection()

    jobs = conn.execute("""
        SELECT j.id, j.title, j.raw_description
        FROM jobs j
        LEFT JOIN job_extractions je ON je.job_id = j.id
        WHERE j.processing_status = 'new' AND je.job_id IS NULL
    """).fetchall()

    print(f"Extracting {len(jobs)} jobs...\n")
    extracted, skipped = 0, 0

    for job in jobs:
        print(f"  [{job['id']}] {job['title']}")
        try:
            result = extract_job(client, job)
            if result is None:
                print(f"    No description — skipping.")
                skipped += 1
                continue

            conn.execute(
                """INSERT INTO job_extractions (job_id, skills, experience_level, key_requirements, extracted_at)
                   VALUES (?, ?, ?, ?, datetime('now'))""",
                (
                    job["id"],
                    json.dumps(result["skills"]),
                    result["experience_level"],
                    json.dumps(result["key_requirements"]),
                ),
            )
            conn.commit()
            extracted += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            skipped += 1

    conn.close()
    print(f"\nDone: {extracted} extracted, {skipped} skipped.")


if __name__ == "__main__":
    run_extraction()
