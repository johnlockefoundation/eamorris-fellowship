-- ============================================================================
-- EA Morris Fellowship — Supabase schema
-- Apply with:  psql "$CONN" -f sql/schema.sql
-- (or via the Supabase SQL editor)
--
-- Two tables power the portal:
--   • jobs     — the curated jobs board (manually maintained by the team)
--   • fellows  — the alumni directory (loaded by the scraper / import scripts)
--
-- ACCESS MODEL
-- ------------
-- The portal is a static site, so the anon key ships to the browser and must
-- be treated as public. Reads are therefore restricted to the `authenticated`
-- role: a row is only returned to a request carrying a valid Supabase Auth
-- session (i.e. someone who signed in with the shared fellowship password).
-- Anonymous visitors get nothing, even though the site URL is public.
-- ============================================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- jobs
-- ---------------------------------------------------------------------------
create table if not exists public.jobs (
  id          uuid primary key default gen_random_uuid(),
  title       text not null,
  company     text,
  location    text,
  work_type   text,           -- e.g. Full-time, Part-time, Contract
  category    text,           -- e.g. Product, Strategy, Finance
  description text,
  url         text,           -- link to the original posting
  tags        text[] default '{}',
  featured    boolean default false,
  posted_at   date default current_date,
  created_at  timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- fellows
-- ---------------------------------------------------------------------------
create table if not exists public.fellows (
  id              uuid primary key default gen_random_uuid(),
  full_name       text not null,
  headline        text,
  current_company text,
  current_title   text,
  city            text,
  state           text,
  country         text,
  cohort_year     int,
  industry        text,
  email           text,
  linkedin_url    text,
  education       text,
  skills          text[] default '{}',
  bio             text,
  photo_url       text,
  -- de-dup key used by the scraper; one row per LinkedIn profile
  linkedin_id     text unique,
  raw             jsonb,        -- full provider payload, for debugging
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- Indexes to speed up directory search
create index if not exists fellows_name_idx    on public.fellows using gin (to_tsvector('simple', coalesce(full_name, '')));
create index if not exists fellows_company_idx on public.fellows using gin (to_tsvector('simple', coalesce(current_company, '')));

-- ---------------------------------------------------------------------------
-- Row Level Security
--   jobs     — signed-in fellows only (curated opportunities)
--   fellows  — PUBLIC: the landing page showcases fellow bios to visitors
-- ---------------------------------------------------------------------------
alter table public.jobs    enable row level security;
alter table public.fellows enable row level security;

drop policy if exists "anon can read jobs"             on public.jobs;
drop policy if exists "anon can read fellows"          on public.fellows;
drop policy if exists "public can read fellows"        on public.fellows;
drop policy if exists "authenticated can read jobs"    on public.jobs;
drop policy if exists "authenticated can read fellows" on public.fellows;

create policy "authenticated can read jobs"
  on public.jobs for select
  to authenticated
  using (true);

create policy "public can read fellows"
  on public.fellows for select
  to anon, authenticated
  using (true);

-- No insert/update/delete policies are defined: only the service_role key
-- (used by local import / scraper scripts, and never shipped to the browser)
-- can write.
-- ============================================================================
