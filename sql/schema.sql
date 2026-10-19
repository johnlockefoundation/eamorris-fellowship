-- ============================================================================
-- EA Morris Fellowship — Supabase schema
-- Run this in the Supabase SQL editor (Dashboard → SQL → New query).
--
-- Two tables power the portal:
--   • jobs     — the curated jobs board (manually maintained by the team)
--   • fellows  — the alumni directory (populated by the LinkedIn scraper and
--                manual edits)
--
-- RLS is enabled on both tables but locked down to anonymous users by
-- default. Because the portal is a static site the anon key ships to the
-- browser, so if you want public read access flip the SELECT policies to
-- `USING (true)`. The login itself is enforced client-side against Supabase
-- Auth (single shared account) — see README for the trade-offs.
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
  id             uuid primary key default gen_random_uuid(),
  full_name      text not null,
  headline       text,
  current_company text,
  current_title  text,
  city           text,
  state          text,
  country        text,
  cohort_year    int,
  industry       text,
  email          text,
  linkedin_url   text,
  education      text,
  skills         text[] default '{}',
  bio            text,
  photo_url      text,
  -- de-dup key used by the scraper; one row per LinkedIn profile
  linkedin_id    text unique,
  raw            jsonb,        -- full LinkedIn payload for debugging
  created_at     timestamptz default now(),
  updated_at     timestamptz default now()
);

-- Convenience indexes for the directory search
create index if not exists fellows_company_idx on public.fellows using gin (to_tsvector('simple', coalesce(current_company, '')));
create index if not exists fellows_name_idx    on public.fellows using gin (to_tsvector('simple', coalesce(full_name, '')));

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------
alter table public.jobs    enable row level security;
alter table public.fellows enable row level security;

-- Demo: allow anonymous READ. Tighten once auth is wired (see note above).
drop policy if exists "anon can read jobs"    on public.jobs;
drop policy if exists "anon can read fellows" on public.fellows;
create policy "anon can read jobs"    on public.jobs    for select using (true);
create policy "anon can read fellows" on public.fellows for select using (true);

-- Service role bypasses RLS, so the scraper (run with the service key from a
-- local machine, never in the browser) can freely INSERT / UPDATE.

-- ---------------------------------------------------------------------------
-- Seed sample data
-- ---------------------------------------------------------------------------
insert into public.jobs (title, company, location, work_type, category, description, url, tags, featured, posted_at) values
  ('Senior Strategy Manager','Stripe','New York, NY','Full-time','Strategy','Drive high-priority strategic initiatives across the platform organisation.','https://example.com/jobs/stripe-strategy','{Strategy,Payments,Hybrid}',true,'2026-10-12'),
  ('Product Manager, Payments','Notion','San Francisco, CA','Full-time','Product','Own the billing and payments roadmap for our self-serve business.','https://example.com/jobs/notion-pm','{Product,Billing,Onsite}',true,'2026-10-09'),
  ('Policy Analyst, Technology','U.S. Department of Commerce','Washington, DC','Full-time','Government','Support the development of policy on emerging technologies and digital trade.','https://example.com/jobs/commerce-policy','{Policy,Public Sector}',false,'2026-10-07')
on conflict do nothing;

insert into public.fellows (full_name, headline, current_company, current_title, city, state, country, cohort_year, industry, email, linkedin_url, education, skills, bio, linkedin_id) values
  ('Amara Okonkwo','Strategy & Operations Lead','Stripe','Strategy & Operations Lead','New York','NY','United States',2019,'Fintech','amara.okonkwo@example.com','https://www.linkedin.com/in/example-amara','University of Pennsylvania, Wharton','{Strategy,Operations,Payments}','Fellow in the inaugural cohort.','demo-amara'),
  ('Daniel Reyes','Product Manager, Growth','Notion','Product Manager, Growth','San Francisco','CA','United States',2020,'Software','daniel.reyes@example.com','https://www.linkedin.com/in/example-daniel','UC Berkeley','{Product,Growth,Data}','Joined Notion after three years in consulting.','demo-daniel'),
  ('Priya Balakrishnan','Investment Associate','Andreessen Horowitz','Investment Associate','Menlo Park','CA','United States',2018,'Venture Capital','priya.b@example.com','https://www.linkedin.com/in/example-priya','Stanford University','{Investing,Fintech,Enterprise}','Invests in early-stage fintech and infrastructure.','demo-priya')
on conflict do nothing;
