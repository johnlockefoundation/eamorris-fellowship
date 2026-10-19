#!/usr/bin/env python3
"""
EA Morris Fellowship — LinkedIn → Supabase scraper.

This runs LOCALLY, not on the website. It reads a list of LinkedIn profile
URLs (from a CSV or a single URL passed on the command line), fetches each
fellow's profile, normalises the fields, and upserts them into the Supabase
`fellows` table.

Important notes
---------------
* Use your own Supabase SERVICE ROLE key here (NOT the anon key) and only on
  your local machine. Never commit it and never expose it in the browser.
* LinkedIn does not like automated scraping. Scraping directly against
  linkedin.com can break without warning and is against LinkedIn's Terms of
  Service. This script therefore defaults to a profile-data API provider
  (Proxycurl) rather than scraping linkedin.com directly. Swap `fetch_profile`
  for your own source if you have a different one.
* Rate limiting and error handling are included, but treat this as a batch
  job you run by hand, not something on a schedule.

Usage
-----
    export SUPABASE_URL="https://YOUR-PROJECT.supabase.co"
    export SUPABASE_SERVICE_ROLE_KEY="..."        # keep private!
    export PROXYCURL_API_KEY="..."                # optional

    # Single profile
    python scraper/scrape.py --url "https://www.linkedin.com/in/janedoe"

    # Batch from CSV (columns: linkedin_url, cohort_year, notes)
    python scraper/scrape.py --csv scraper/fellows_input.csv

    # Write to Supabase (default is dry-run / preview only)
    python scraper/scrape.py --csv scraper/fellows_input.csv --push
"""

import argparse
import csv
import os
import sys
import time

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
PROXYCURL_KEY = os.environ.get("PROXYCURL_API_KEY", "")

PROXYCURL_ENDPOINT = "https://api.proxycurl.com/api/v2/linkedin"
REQUEST_TIMEOUT = 20
SLEEP_BETWEEN = 1.0  # seconds between requests, to stay polite

# Map a Proxycurl profile onto our `fellows` schema (see sql/schema.sql).
def normalise(profile, linkedin_url, extra=None):
    extra = extra or {}
    return {
        "full_name": profile.get("full_name") or "",
        "headline": profile.get("headline") or "",
        "current_company": profile.get("company_name") or "",
        "current_title": profile.get("title") or "",
        "city": profile.get("city") or "",
        "state": profile.get("state") or "",
        "country": profile.get("country") or "",
        "cohort_year": _int(extra.get("cohort_year")),
        "industry": profile.get("industry") or "",
        "email": profile.get("email") or "",
        "linkedin_url": linkedin_url,
        "education": _education(profile),
        "skills": (profile.get("skills") or [])[:12],
        "bio": profile.get("summary") or "",
        "photo_url": profile.get("profile_pic_url") or "",
        "linkedin_id": _linkedin_id(linkedin_url),
        "raw": profile,
    }


def _int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _education(profile):
    exp = profile.get("experiences") or []
    if exp:
        return exp[0].get("institute_name") or ""
    return ""


def _linkedin_id(url):
    # https://www.linkedin.com/in/janedoe/ → janedoe
    url = (url or "").strip().rstrip("/")
    if "/in/" in url:
        return url.split("/in/")[-1].split("/")[0].lower()
    return url.lower()


def fetch_profile(linkedin_url):
    """Return a dict of profile data. Swap this function to change the source."""
    if PROXYCURL_KEY:
        resp = requests.get(
            PROXYCURL_ENDPOINT,
            params={"url": linkedin_url, "use_cache": "if-present"},
            headers={"Authorization": f"Bearer {PROXYCURL_KEY}"},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    # No API key configured — emit a stub so the pipeline can still be tested
    # end-to-end before you pick a data provider.
    print(
        "  ! No PROXYCURL_API_KEY set — emitting a placeholder record. "
        "Set an API key (or replace fetch_profile) to pull real data.",
        file=sys.stderr,
    )
    return {
        "full_name": _linkedin_id(linkedin_url).replace("-", " ").title(),
        "headline": "",
        "summary": "",
        "city": "",
        "state": "",
        "country": "",
        "industry": "",
        "company_name": "",
        "title": "",
        "skills": [],
        "experiences": [],
        "profile_pic_url": "",
        "email": "",
    }


def upsert(record):
    if not SUPABASE_URL or not SERVICE_ROLE:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to push.")
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/fellows",
        params={"on_conflict": "linkedin_id"},
        headers={
            "apikey": SERVICE_ROLE,
            "Authorization": f"Bearer {SERVICE_ROLE}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation",
        },
        json=record,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.status_code


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = (row.get("linkedin_url") or "").strip()
            if url:
                yield url, row


def main():
    ap = argparse.ArgumentParser(description="LinkedIn → Supabase fellow scraper")
    ap.add_argument("--url", help="A single LinkedIn profile URL")
    ap.add_argument("--csv", help="CSV of profiles (needs a linkedin_url column)")
    ap.add_argument("--push", action="store_true", help="Write to Supabase (default: dry run)")
    args = ap.parse_args()

    targets = []
    if args.url:
        targets.append((args.url, {}))
    elif args.csv:
        targets = list(read_csv(args.csv))
    else:
        ap.error("Provide --url or --csv")

    if args.push and (not SUPABASE_URL or not SERVICE_ROLE):
        raise SystemExit("--push requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")

    print(f"Processing {len(targets)} profile(s). Mode: {'PUSH' if args.push else 'DRY-RUN'}\n")

    ok = failed = 0
    for linkedin_url, extra in targets:
        print(f"→ {linkedin_url}")
        try:
            profile = fetch_profile(linkedin_url)
            if not profile:
                print("  · not found, skipping")
                failed += 1
                continue
            record = normalise(profile, linkedin_url, extra)
            preview = {k: v for k, v in record.items() if k != "raw"}
            if args.push:
                status = upsert(record)
                print(f"  ✓ upserted (HTTP {status}): {preview['full_name']} — {preview['current_company']}")
            else:
                print(f"  · would upsert: {preview}")
            ok += 1
        except requests.HTTPError as e:
            print(f"  ✗ HTTP error: {e}", file=sys.stderr)
            failed += 1
        except Exception as e:  # noqa: BLE001 - batch job, keep going
            print(f"  ✗ error: {e}", file=sys.stderr)
            failed += 1
        time.sleep(SLEEP_BETWEEN)

    print(f"\nDone. {ok} succeeded, {failed} failed/skipped.")


if __name__ == "__main__":
    main()
