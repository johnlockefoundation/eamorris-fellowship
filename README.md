# EA Morris Fellowship — Portal POC

A static proof-of-concept for the fellowship portal, deployable on **GitHub
Pages**. It includes a password-protected login and, once signed in, two core
features:

1. **Curated jobs board** — opportunities maintained by the programme team.
2. **Fellow directory** — searchable alumni database (by name, company, place
   of residence, industry, cohort).

It runs **fully in demo mode with no backend**, using the bundled sample data,
so it can be shown immediately. Attach Supabase when you're ready to go live.

---

## What's in the box

```
index.html        Login page (single shared password)
dashboard.html    Post-login portal: Jobs Board + Fellow Directory
style.css         Brand styling (teal / cream, Fraunces + Mulish)
config.js         Supabase credentials + program settings  ← edit this
auth.js           Auth layer (Supabase Auth, or demo mode)
data.js           Data layer (Supabase tables, or demo data)
dashboard.js      Filtering, rendering, detail drawer
demo-data.js      Sample jobs + fellows for the demo
sql/schema.sql    Supabase tables (jobs, fellows) + sample rows
scraper/          Local LinkedIn → Supabase scraper (not part of the site)
Stylesheet+Logos/ Brand assets
```

---

## Run the demo (no backend needed)

Just open `index.html` in a browser. The demo password is:

```
eamorris2026
```

(The password is set in `config.js` → `DEMO_PASSWORD`.)

---

## Deploy to GitHub Pages

1. Push this folder to a GitHub repository.
2. Repo → **Settings → Pages** → Source: **Deploy from a branch** →
   Branch: `main` / `/ (root)`.
3. The site will be live at `https://<your-user>.github.io/<repo>/`.

No build step required — it's plain HTML/CSS/JS.

---

## Go live with Supabase

The portal is wired to Supabase but falls back to demo mode until you add
credentials.

### 1. Create the database

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL → New query**, paste the contents of `sql/schema.sql`, run it.
3. Confirm the `jobs` and `fellows` tables appear, with sample rows.

### 2. Create the single shared account

Everyone shares one login (no per-fellow accounts):

1. **Authentication → Users → Add user** → create a user with a fixed email
   (e.g. `fellows@eamorris.org`) and the password you'll distribute.
2. Copy that email into `config.js` → `SHARED_EMAIL`.

> The email is only used internally to identify the shared account — it's
> never shown in the UI; the login form asks for the password only.

### 3. Add your credentials

Edit `config.js`:

```js
SUPABASE_URL: "https://YOUR-PROJECT.supabase.co",
SUPABASE_ANON_KEY: "YOUR-ANON-KEY",
SHARED_EMAIL: "fellows@eamorris.org",
```

Once both values are real, the site automatically switches to **Live** mode.

> **A note on security:** the `anon` key is public by design and ships to the
> browser. The RLS policies in `schema.sql` currently allow anonymous *read*
> of jobs and fellows so the static site can display them. This means anyone
> who finds the URL can read the data — they just can't sign in to see the
> rendered UI. If the directory should be genuinely private, put an edge
> function / stricter RLS in front, or move read access behind Supabase Auth.
> This is a known trade-off for a static-site POC — flagged for the boss
> discussion.

---

## Managing the jobs board

Add or edit rows in the **`jobs`** table (Supabase → Table editor). Each row:

| column     | meaning                                   |
|------------|-------------------------------------------|
| title      | Role title                                |
| company    | Employer                                  |
| location   | City / region shown on the card           |
| work_type  | Full-time, Contract, Remote…              |
| category   | Used for the category filter              |
| description| Short blurb on the card                   |
| url        | Link out to the posting                   |
| tags       | Optional `text[]` of extra tags           |
| featured   | Highlights the card                       |
| posted_at  | Date used for sorting                     |

Edits show up on the site with no code changes.

---

## The LinkedIn scraper

`scraper/scrape.py` populates the `fellows` table. It is a **local script**,
separate from the site, run by the team.

```bash
cd scraper
pip install -r requirements.txt

export SUPABASE_URL="https://YOUR-PROJECT.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="..."   # keep this PRIVATE
export PROXYCURL_API_KEY="..."           # optional, real data source

# Preview without writing
python scrape.py --csv fellows_input.csv

# Push to Supabase
python scrape.py --csv fellows_input.csv --push
```

**A note on LinkedIn:** scraping `linkedin.com` directly is fragile and
against LinkedIn's Terms of Service. This script defaults to a profile-data
API (Proxycurl) and only needs a list of profile URLs — see
`scraper/fellows_input.csv`. Swap the `fetch_profile` function if you use a
different source. Always run this locally and keep the service-role key off
the website.

---

## Customising the look

- **Colours** — `style.css` → `:root` variables. The primary teal
  (`--teal-800: #12343A`) is sampled from the EA Morris logo.
- **Logos** — live in `Stylesheet+Logos/`; referenced from the HTML.
- **Demo data** — edit `demo-data.js` to change what the POC shows.
