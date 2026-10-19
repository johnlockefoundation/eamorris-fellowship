# EA Morris Fellowship — Portal POC

A static portal for the fellowship, deployed on **GitHub Pages** and backed by
**Supabase**. It has a password-protected login and, once signed in, two core
features:

1. **Curated jobs board** — opportunities maintained by the programme team.
2. **Fellow directory** — searchable alumni directory (by name, company, place
   of residence, industry, cohort).

> **The login is real.** All data is stored in Supabase and reads are gated by
> Row Level Security: a request without a valid signed-in session gets nothing
> back, even though the site URL itself is public.

---

## Live environment

| | |
|---|---|
| **Site** | https://johnlockefoundation.github.io/eamorris-fellowship/ |
| **Repo** | https://github.com/johnlockefoundation/eamorris-fellowship |
| **Supabase project** | `eamorris-fellowship` (`iwmyqbensppmrstykqpd`) |
| **Shared login** | `fellows@eamorris.org` *(password distributed out-of-band — not in this repo)* |

---

## What's in the box

```
index.html        Login page (single shared password)
dashboard.html    Post-login portal: Jobs Board + Fellow Directory
style.css         Brand styling (teal / cream, Fraunces + Mulish)
config.js         Supabase URL + public anon key + program settings
auth.js           Auth layer (Supabase Auth, or demo mode)
data.js           Data layer (Supabase tables, or demo data)
dashboard.js      Filtering, rendering, detail drawer
demo-data.js      Sample data — used ONLY when Supabase isn't configured
sql/schema.sql    Tables (jobs, fellows) + RLS policies
sql/seed_demo.sql Optional fake rows for a sandbox database
scraper/          Local LinkedIn → Supabase scraper (not part of the site)
Stylesheet+Logos/ Brand assets
```

---

## Security model

The site is static, so the Supabase **anon key ships to the browser and must be
treated as public**. That's fine, because the key alone grants nothing:

- `sql/schema.sql` enables RLS on both tables and defines **read policies for
  the `authenticated` role only** — no `anon` access.
- A read without a valid Supabase Auth session returns an empty result set.
- The only writes come from the `service_role` key, which is used by local
  scripts and never shipped to the browser.

So the shared password is the actual gate. A few consequences worth knowing:

- **Rotate the shared password** whenever a fellow leaves, from Supabase →
  Authentication → Users. Everyone shares one account, so there's no per-person
  revocation.
- Anyone with the password can read the whole directory. That's the intended
  model for a single shared login.
- Real fellow data must **never** be committed to this repo — it's public. Keep
  imports and exports in the git-ignored `data/` folder.

---

## Managing the jobs board

Add or edit rows in the **`jobs`** table (Supabase → Table editor):

| column      | meaning                            |
|-------------|------------------------------------|
| title       | Role title                         |
| company     | Employer                           |
| location    | City / region shown on the card    |
| work_type   | Full-time, Contract, Remote…       |
| category    | Used for the category filter       |
| description | Short blurb on the card            |
| url         | Link out to the posting            |
| tags        | Optional `text[]` of extra tags    |
| featured    | Highlights the card                |
| posted_at   | Date used for sorting              |

Edits show up on the site with no code changes. *(The 8 jobs currently loaded
are placeholders — replace them with real roles.)*

---

## Fellow directory data

The real roster lives in the Supabase `fellows` table. To load a list of names:

```bash
# names.txt = one full name per line, kept in the git-ignored data/ folder
psql "$CONN" -f data/import_fellows.sql   # generated from the names file
```

Right now the table holds **231 names and nothing else** (no company, location,
or title), so the directory's company/location filters have nothing to work
with yet. Enriching the records is the next step — see below.

---

## The LinkedIn scraper

`scraper/scrape.py` enriches `fellows` records (company, title, location,
industry…). It is a **local script**, separate from the site, run by the team.

```bash
cd scraper
pip install -r requirements.txt

export SUPABASE_URL="https://iwmyqbensppmrstykqpd.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="..."   # keep this PRIVATE
export PROXYCURL_API_KEY="..."           # optional, real data source

# Preview without writing
python scrape.py --csv fellows_input.csv

# Push to Supabase
python scrape.py --csv fellows_input.csv --push
```

**A note on LinkedIn:** scraping `linkedin.com` directly is fragile and against
LinkedIn's Terms of Service. This script defaults to a profile-data API
(Proxycurl) and only needs a list of profile URLs. Swap `fetch_profile` if you
use a different source. Always run it locally and keep the service-role key off
the website.

---

## Interim enrichment from the bios

Until a LinkedIn data-provider key is available, `scraper/parse_bios.py`
derives what it can from the written bios: job title, employer, current city,
education and a coarse industry bucket. It is deliberately conservative — a
field is only written when a clear pattern matches, and the LinkedIn scrape
supersedes these values when it runs.

```bash
# Preview coverage and a few examples
python scraper/parse_bios.py --csv data/fellows_bios.csv --sample 20

# Generate UPDATE statements, then apply them
python scraper/parse_bios.py --csv data/fellows_bios.csv \
    --sql data/import_fellow_details.sql
psql "$CONN" -f data/import_fellow_details.sql
```

Roughly: title ~83%, employer ~70%, education ~72%, industry ~90%, city ~22%.
The bios rarely state a current city, so location stays mostly empty until the
scrape fills it in.

---

## Local development / demo mode

The portal falls back to **demo mode** (bundled sample data, no backend) when
`config.js` has no real Supabase credentials. To preview locally:

```bash
python3 -m http.server 8000   # then open http://localhost:8000
```

Demo-mode password: `eamorris2026` (`config.js` → `DEMO_PASSWORD`). This only
applies when Supabase is *not* configured — it is unrelated to the live login.

---

## Deploying

Plain HTML/CSS/JS, no build step. Push to `main`; GitHub Pages redeploys
automatically.

```bash
git add -A && git commit -m "..." && git push origin main
```

---

## Customising the look

- **Colours** — `style.css` → `:root`. Primary teal `--teal-800: #12343A` is
  sampled from the EA Morris logo.
- **Type** — Fraunces (headings) + Mulish (body), standing in for the brand's
  IvyPresto Headline + Muli.
- **Logos** — `Stylesheet+Logos/`, referenced from the HTML.
