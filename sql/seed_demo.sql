-- ============================================================================
-- OPTIONAL demo seed data — for a sandbox database only.
-- Do NOT run this against the live fellowship database (it would mix fake
-- people into the real directory).
--   psql "$CONN" -f sql/seed_demo.sql
-- ============================================================================

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
