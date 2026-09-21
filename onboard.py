import psycopg

from db import get_connection, init_db
from fetch import FETCHERS

VALID_ATS = list(FETCHERS.keys())
CANCEL_WORDS = ("q", "quit", "cancel")


class Cancelled(Exception):
    pass


def resolve(ats: str, ats_identifier: str) -> dict:
    try:
        jobs = FETCHERS[ats](ats_identifier)
    except Exception as e:
        return {"status": "hard_failure", "message": str(e)}
    if not jobs:
        return {"status": "zero_results"}
    return {"status": "success", "jobs": jobs}


def _check_cancel(value: str):
    if value.strip().lower() in CANCEL_WORDS:
        raise Cancelled()


def _prompt(label: str) -> str:
    value = input(f"{label} (or 'q' to cancel): ").strip()
    _check_cancel(value)
    while not value:
        value = input(f"{label} (required, or 'q' to cancel): ").strip()
        _check_cancel(value)
    return value


def _prompt_ats() -> str:
    ats = input(f"ATS platform ({'/'.join(VALID_ATS)}, or 'q' to cancel): ").strip().lower()
    _check_cancel(ats)
    while ats not in VALID_ATS:
        print(f"  Unsupported ATS '{ats}'. Must be one of: {', '.join(VALID_ATS)}.")
        ats = input(f"ATS platform ({'/'.join(VALID_ATS)}, or 'q' to cancel): ").strip().lower()
        _check_cancel(ats)
    return ats


def _confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/n]: ").strip().lower() in ("y", "yes")


def add_company(conn):
    print("\n--- Add a new company ---")
    name = _prompt("Company name")
    careers_url = _prompt("Careers URL")
    ats = _prompt_ats()
    ats_identifier = _prompt("ATS slug")

    while True:
        result = resolve(ats, ats_identifier)

        if result["status"] == "success":
            jobs = result["jobs"]
            print(f"\n  Found {len(jobs)} job(s) on {ats} board '{ats_identifier}'. Sample titles:")
            for job in jobs[:5]:
                print(f"    - {job['title']}")
            if not _confirm("\n  Add this company?"):
                print("  Aborted — nothing written.")
                return
            try:
                conn.execute(
                    """INSERT INTO companies (name, careers_url, ats, ats_identifier, active)
                       VALUES (%s, %s, %s, %s, TRUE)""",
                    (name, careers_url, ats, ats_identifier),
                )
                conn.commit()
                print(f"  Added '{name}'.")
            except psycopg.errors.UniqueViolation:
                conn.rollback()
                print(f"  A company named '{name}' already exists — nothing written.")
            return

        if result["status"] == "zero_results":
            print(f"\n  Slug '{ats_identifier}' returned 0 jobs — please confirm this is correct.")
        else:
            print(f"\n  Slug not found — check for typos. ({result['message']})")

        if not _confirm("  Re-enter platform/slug?"):
            print("  Aborted — nothing written.")
            return
        ats = _prompt_ats()
        ats_identifier = _prompt("ATS slug")


def toggle_active(conn):
    print("\n--- Toggle active status ---")
    companies = conn.execute("SELECT id, name, active FROM companies ORDER BY name").fetchall()
    if not companies:
        print("  No companies found.")
        return

    for i, c in enumerate(companies, start=1):
        status = "active" if c["active"] else "inactive"
        print(f"  {i}) {c['name']} ({status})")

    choice = input("\n  Select a company by number (or blank to cancel): ").strip()
    if not choice:
        print("  Cancelled.")
        return
    try:
        idx = int(choice) - 1
        company = companies[idx]
    except (ValueError, IndexError):
        print("  Invalid selection.")
        return

    new_active = not company["active"]
    new_label = "active" if new_active else "inactive"
    if not _confirm(f"  Set '{company['name']}' to {new_label}?"):
        print("  Cancelled.")
        return

    conn.execute("UPDATE companies SET active = %s WHERE id = %s", (new_active, company["id"]))
    conn.commit()
    verb = "will be included in future fetches" if new_active else "will be skipped by future fetches"
    print(f"  '{company['name']}' is now {new_label} — {verb}.")


def main():
    init_db()
    conn = get_connection()

    while True:
        print("\n=== Company Onboarding ===")
        print("1) Add a new company")
        print("2) Toggle active status on an existing company")
        print("3) Quit")
        choice = input("Choice: ").strip()

        if choice == "1":
            try:
                add_company(conn)
            except Cancelled:
                print("  Cancelled — nothing written.")
        elif choice == "2":
            toggle_active(conn)
        elif choice == "3":
            break
        else:
            print("Invalid choice.")

    conn.close()


if __name__ == "__main__":
    main()
