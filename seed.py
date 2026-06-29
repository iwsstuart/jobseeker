from db import get_connection, init_db

# ats_identifier values are the board token / slug each ATS uses in its API.
# Greenhouse: boards-api.greenhouse.io/v1/boards/{token}/jobs
# Ashby:      api.ashbyhq.com/posting-api/job-board/{slug}
# These are best-guess slugs based on company names — verify by running fetch.py
# and adjusting any that return a 404.
COMPANIES = [
    # Greenhouse (v1)
    {
        "name": "Teads",
        "careers_url": "https://www.teads.com/teads-careers/",
        "ats": "greenhouse",
        "ats_identifier": "teads1",
        "active": True,
    },
    {
        "name": "Overstory",
        "careers_url": "https://www.overstory.com/careers",
        "ats": "greenhouse",
        "ats_identifier": "overstory",
        "active": True,
    },
    {
        "name": "Carbon Direct",
        "careers_url": "https://www.carbon-direct.com/careers#jobPostings",
        "ats": "greenhouse",
        "ats_identifier": "carbondirect",
        "active": True,
    },
    {
        "name": "Sigma",
        "careers_url": "https://www.sigmacomputing.com/company/careers",
        "ats": "greenhouse",
        "ats_identifier": "sigmacomputing",
        "active": True,
    },
    # Ashby (v1)
    {
        "name": "Zapier",
        "careers_url": "https://zapier.com/jobs#job-openings",
        "ats": "ashby",
        "ats_identifier": "zapier",
        "active": True,
    },
    {
        "name": "Headway",
        "careers_url": "https://headway.co/careers",
        "ats": "ashby",
        "ats_identifier": "headway",
        "active": True,
    },
    # Second pass — inactive until fetchers are built
    {
        "name": "Wherobots",
        "careers_url": "https://wherobots.com/careers/",
        "ats": "rippling",
        "ats_identifier": None,
        "active": False,
    },
    {
        "name": "Inspiration Mobility",
        "careers_url": "https://inspirationmobility.com/about/careers",
        "ats": "rippling",
        "ats_identifier": None,
        "active": False,
    },
    {
        "name": "Carto",
        "careers_url": "https://carto.com/careers/",
        "ats": "pinpoint",
        "ats_identifier": None,
        "active": False,
    },
    {
        "name": "Electricity Maps",
        "careers_url": "https://careers.electricitymaps.com/",
        "ats": "unknown",
        "ats_identifier": None,
        "active": False,
    },
    {
        "name": "Chargetrip",
        "careers_url": "https://www.chargetrip.com/careers",
        "ats": "unknown",
        "ats_identifier": None,
        "active": False,
    },
]


def seed():
    init_db()
    conn = get_connection()
    for c in COMPANIES:
        conn.execute(
            """INSERT OR IGNORE INTO companies (name, careers_url, ats, ats_identifier, active)
               VALUES (?, ?, ?, ?, ?)""",
            (c["name"], c["careers_url"], c["ats"], c["ats_identifier"], 1 if c["active"] else 0),
        )
    conn.commit()
    conn.close()
    print(f"Seeded {len(COMPANIES)} companies.")


if __name__ == "__main__":
    seed()
