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
    {
        "name": "Crusoe",
        "careers_url": "https://www.crusoe.ai/about/careers",
        "ats": "ashby",
        "ats_identifier": "Crusoe",
        "active": True,
    },
    {
        "name": "Aurora Solar",
        "careers_url": "https://aurorasolar.com/careers/",
        "ats": "ashby",
        "ats_identifier": "aurorasolar",
        "active": True,
    },
    {
        "name": "Harvey",
        "careers_url": "https://www.harvey.ai/careers",
        "ats": "ashby",
        "ats_identifier": "harvey",
        "active": True,
    },
    # Rippling / Pinpoint (added once those fetchers landed)
    {
        "name": "Wherobots",
        "careers_url": "https://wherobots.com/careers/",
        "ats": "rippling",
        "ats_identifier": "wherobots",
        "active": True,
    },
    {
        "name": "Inspiration Mobility",
        "careers_url": "https://inspirationmobility.com/about/careers",
        "ats": "rippling",
        "ats_identifier": "inspiration-mobility",
        "active": True,
    },
    {
        "name": "Carto",
        "careers_url": "https://carto.com/careers/",
        "ats": "pinpoint",
        "ats_identifier": "carto",
        "active": True,
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
        # `active` is deliberately excluded from the UPDATE SET — it's
        # user-controlled via onboard.py's toggle flow, and a plain upsert
        # would silently undo that on every run otherwise.
        conn.execute(
            """INSERT INTO companies (name, careers_url, ats, ats_identifier, active)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT(name) DO UPDATE SET
                   careers_url = excluded.careers_url,
                   ats = excluded.ats,
                   ats_identifier = excluded.ats_identifier""",
            (c["name"], c["careers_url"], c["ats"], c["ats_identifier"], c["active"]),
        )
    conn.commit()
    conn.close()
    print(f"Seeded {len(COMPANIES)} companies.")


if __name__ == "__main__":
    seed()
