import json
import os
import anthropic
from db import get_connection

MODEL = "claude-haiku-4-5-20251001"

PROFILE_PATH = os.path.join(os.path.dirname(__file__), "profile_prompt.md")

TOOL = {
    "name": "evaluate_match",
    "description": "Evaluate whether a job posting is a good match for the candidate profile.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_match": {
                "type": "boolean",
                "description": "True if the role is a match or borderline match worth surfacing; false if clearly not a match.",
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "Plain-English explanation of why the role is or isn't a match. "
                    "Reference specific aspects of the role and the candidate profile. "
                    "2-4 sentences."
                ),
            },
        },
        "required": ["is_match", "reasoning"],
    },
}


def match_job(client: anthropic.Anthropic, profile: str, job: dict) -> dict | None:
    prompt = f"""{profile}

---

Now evaluate the following job:

**Title:** {job["title"]}
**Company:** {job["company"]}
**Experience level:** {job["experience_level"]}
**Skills:** {", ".join(json.loads(job["skills"]))}
**Key requirements:**
{chr(10).join(f"- {r}" for r in json.loads(job["key_requirements"]))}
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "evaluate_match"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "evaluate_match":
            return block.input
    return None


def run_matching():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY environment variable not set.")

    with open(PROFILE_PATH) as f:
        profile = f.read()

    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection()

    jobs = conn.execute("""
        SELECT j.id, j.title, c.name AS company,
               je.skills, je.experience_level, je.key_requirements
        FROM jobs j
        JOIN companies c ON c.id = j.company_id
        JOIN job_extractions je ON je.job_id = j.id
        LEFT JOIN match_results mr ON mr.job_id = j.id
        WHERE j.processing_status = 'new' AND mr.job_id IS NULL
    """).fetchall()

    print(f"Matching {len(jobs)} jobs...\n")
    matched, not_matched, skipped = 0, 0, 0

    for job in jobs:
        print(f"  [{job['id']}] {job['title']} @ {job['company']}")
        try:
            result = match_job(client, profile, job)
            if result is None:
                print(f"    No result — skipping.")
                skipped += 1
                continue

            conn.execute(
                """INSERT INTO match_results (job_id, is_match, reasoning, evaluated_at)
                   VALUES (?, ?, ?, datetime('now'))""",
                (job["id"], 1 if result["is_match"] else 0, result["reasoning"]),
            )
            conn.execute(
                "UPDATE jobs SET processing_status = 'evaluated' WHERE id = ?",
                (job["id"],),
            )
            conn.commit()

            label = "MATCH" if result["is_match"] else "no match"
            print(f"    {label}: {result['reasoning'][:80]}...")
            if result["is_match"]:
                matched += 1
            else:
                not_matched += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            skipped += 1

    conn.close()
    print(f"\nDone: {matched} matched, {not_matched} not matched, {skipped} skipped.")


if __name__ == "__main__":
    run_matching()
