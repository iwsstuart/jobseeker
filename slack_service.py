import hashlib
import hmac
import json
import os
import threading
import time

import psycopg
import requests
from flask import Flask, request, jsonify

from db import get_connection, init_db
from onboard import resolve, VALID_ATS

app = Flask(__name__)

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
ALLOWED_USER_IDS = {u for u in os.environ.get("SLACK_ALLOWED_USER_IDS", "").split(",") if u}

SLACK_API = "https://slack.com/api"


# --- Security ---------------------------------------------------------

def verify_slack_signature(req) -> bool:
    if not SLACK_SIGNING_SECRET:
        return False
    timestamp = req.headers.get("X-Slack-Request-Timestamp", "")
    if not timestamp:
        return False
    try:
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
    except ValueError:
        return False
    basestring = f"v0:{timestamp}:{req.get_data(as_text=True)}"
    computed = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(), basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, req.headers.get("X-Slack-Signature", ""))


def is_allowed(user_id: str) -> bool:
    return bool(user_id) and user_id in ALLOWED_USER_IDS


def _unauthorized_message():
    return jsonify({"response_type": "ephemeral", "text": "You're not authorized to use this command."})


# --- Slack API helpers --------------------------------------------------

def slack_post(url: str, payload: dict):
    requests.post(url, json=payload, timeout=10)


def views_open(trigger_id: str, view: dict):
    requests.post(
        f"{SLACK_API}/views.open",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={"trigger_id": trigger_id, "view": view},
        timeout=10,
    )


# --- Modal builders -------------------------------------------------------

def add_company_modal(response_url: str) -> dict:
    return {
        "type": "modal",
        "callback_id": "add_company_modal",
        "private_metadata": json.dumps({"response_url": response_url}),
        "title": {"type": "plain_text", "text": "Add a company"},
        "submit": {"type": "plain_text", "text": "Check"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "name_block",
                "label": {"type": "plain_text", "text": "Company name"},
                "element": {"type": "plain_text_input", "action_id": "name_input"},
            },
            {
                "type": "input",
                "block_id": "url_block",
                "label": {"type": "plain_text", "text": "Careers URL"},
                "element": {"type": "plain_text_input", "action_id": "url_input"},
            },
            {
                "type": "input",
                "block_id": "ats_block",
                "label": {"type": "plain_text", "text": "ATS platform"},
                "element": {
                    "type": "static_select",
                    "action_id": "ats_select",
                    "options": [
                        {"text": {"type": "plain_text", "text": a}, "value": a} for a in VALID_ATS
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "slug_block",
                "label": {"type": "plain_text", "text": "ATS slug"},
                "element": {"type": "plain_text_input", "action_id": "slug_input"},
            },
        ],
    }


def toggle_message() -> dict:
    conn = get_connection()
    companies = conn.execute("SELECT id, name, active FROM companies ORDER BY name").fetchall()
    conn.close()
    options = [
        {
            "text": {"type": "plain_text", "text": f"{c['name']} ({'active' if c['active'] else 'inactive'})"},
            "value": str(c["id"]),
        }
        for c in companies
    ]
    return {
        "response_type": "ephemeral",
        "blocks": [
            {
                "type": "section",
                "block_id": "toggle_select_block",
                "text": {"type": "mrkdwn", "text": "Select a company to toggle active status:"},
                "accessory": {
                    "type": "static_select",
                    "action_id": "toggle_select",
                    "placeholder": {"type": "plain_text", "text": "Select a company"},
                    "options": options,
                },
            }
        ],
    }


# --- Async resolver worker -----------------------------------------------

def run_resolver_check(response_url: str, name: str, careers_url: str, ats: str, ats_identifier: str):
    try:
        result = resolve(ats, ats_identifier)
    except Exception as e:
        slack_post(response_url, {"replace_original": True, "text": f"Unexpected error checking slug: {e}"})
        return

    if result["status"] == "success":
        jobs = result["jobs"]
        pending = json.dumps(
            {"name": name, "careers_url": careers_url, "ats": ats, "ats_identifier": ats_identifier}
        )
        sample = "\n".join(f"- {j['title']}" for j in jobs[:5])
        text = f"Found {len(jobs)} job(s) on {ats} board '{ats_identifier}'. Sample titles:\n{sample}"
        slack_post(response_url, {
            "replace_original": True,
            "text": text,
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": text}},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button", "action_id": "confirm_add_company", "style": "primary",
                            "text": {"type": "plain_text", "text": "Confirm"}, "value": pending,
                        },
                        {
                            "type": "button", "action_id": "reject_add_company",
                            "text": {"type": "plain_text", "text": "Reject"}, "value": "reject",
                        },
                    ],
                },
            ],
        })
    elif result["status"] == "zero_results":
        slack_post(response_url, {
            "replace_original": True,
            "text": f"Slug '{ats_identifier}' returned 0 jobs — please confirm this is correct and try again.",
        })
    else:
        slack_post(response_url, {
            "replace_original": True,
            "text": f"Slug not found — check for typos. ({result['message']})",
        })


# --- Routes ----------------------------------------------------------------

@app.route("/slack/command", methods=["POST"])
def slack_command():
    if not verify_slack_signature(request):
        return "invalid signature", 401

    form = request.form
    user_id = form.get("user_id", "")
    command = form.get("command", "")

    if not is_allowed(user_id):
        return _unauthorized_message()

    if command == "/add-company":
        views_open(form.get("trigger_id", ""), add_company_modal(form.get("response_url", "")))
        return "", 200

    if command == "/toggle-company":
        return jsonify(toggle_message())

    return jsonify({"response_type": "ephemeral", "text": f"Unknown command '{command}'."})


@app.route("/slack/interactions", methods=["POST"])
def slack_interactions():
    if not verify_slack_signature(request):
        return "invalid signature", 401

    payload = json.loads(request.form.get("payload", "{}"))
    user_id = payload.get("user", {}).get("id", "")

    if not is_allowed(user_id):
        return "", 200

    if payload.get("type") == "view_submission":
        return handle_view_submission(payload)

    if payload.get("type") == "block_actions":
        return handle_block_action(payload)

    return "", 200


def handle_view_submission(payload):
    view = payload["view"]
    if view.get("callback_id") != "add_company_modal":
        return "", 200

    values = view["state"]["values"]
    name = values["name_block"]["name_input"]["value"]
    careers_url = values["url_block"]["url_input"]["value"]
    ats = values["ats_block"]["ats_select"]["selected_option"]["value"]
    ats_identifier = values["slug_block"]["slug_input"]["value"]
    response_url = json.loads(view.get("private_metadata") or "{}").get("response_url")

    threading.Thread(
        target=run_resolver_check, args=(response_url, name, careers_url, ats, ats_identifier), daemon=True
    ).start()

    return jsonify({})


def handle_block_action(payload):
    action = payload["actions"][0]
    action_id = action["action_id"]
    response_url = payload.get("response_url")

    if action_id == "confirm_add_company":
        pending = json.loads(action["value"])
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO companies (name, careers_url, ats, ats_identifier, active)
                   VALUES (%s, %s, %s, %s, TRUE)""",
                (pending["name"], pending["careers_url"], pending["ats"], pending["ats_identifier"]),
            )
            conn.commit()
            slack_post(response_url, {"replace_original": True, "text": f"Added '{pending['name']}'."})
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            slack_post(response_url, {
                "replace_original": True,
                "text": f"A company named '{pending['name']}' already exists — nothing written.",
            })
        finally:
            conn.close()

    elif action_id == "reject_add_company":
        slack_post(response_url, {"replace_original": True, "text": "Aborted — nothing written."})

    elif action_id == "toggle_select":
        company_id = action["selected_option"]["value"]
        conn = get_connection()
        company = conn.execute("SELECT id, name, active FROM companies WHERE id = %s", (company_id,)).fetchone()
        conn.close()
        new_label = "inactive" if company["active"] else "active"
        pending = json.dumps({"id": company["id"], "new_active": not company["active"], "name": company["name"]})
        slack_post(response_url, {
            "replace_original": True,
            "text": f"Set '{company['name']}' to {new_label}?",
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"Set '{company['name']}' to {new_label}?"}},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button", "action_id": "confirm_toggle", "style": "primary",
                            "text": {"type": "plain_text", "text": "Confirm"}, "value": pending,
                        },
                        {
                            "type": "button", "action_id": "cancel_toggle",
                            "text": {"type": "plain_text", "text": "Cancel"}, "value": "cancel",
                        },
                    ],
                },
            ],
        })

    elif action_id == "confirm_toggle":
        pending = json.loads(action["value"])
        conn = get_connection()
        conn.execute("UPDATE companies SET active = %s WHERE id = %s", (pending["new_active"], pending["id"]))
        conn.commit()
        conn.close()
        new_label = "active" if pending["new_active"] else "inactive"
        slack_post(response_url, {
            "replace_original": True, "text": f"'{pending['name']}' is now {new_label}.",
        })

    elif action_id == "cancel_toggle":
        slack_post(response_url, {"replace_original": True, "text": "Cancelled."})

    return "", 200


if __name__ == "__main__":
    init_db()
    app.run(port=int(os.environ.get("PORT", 8080)))
