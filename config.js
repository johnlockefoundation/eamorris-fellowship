/**
 * EA Morris Fellowship — application configuration
 * -------------------------------------------------
 * Fill these in with your Supabase project credentials to enable the live
 * backend. While they are left as placeholders the site runs in DEMO MODE,
 * which uses the bundled sample data so the POC can be shown without a
 * backend attached.
 *
 * Supabase dashboard → Project Settings → API:
 *   - Project URL        → SUPABASE_URL
 *   - anon public key    → SUPABASE_ANON_KEY
 */

window.EAM_CONFIG = {
  // ---- Supabase -----------------------------------------------------------
  // Leave as-is to run in demo mode. Replace to go live.
  SUPABASE_URL: "https://YOUR-PROJECT.supabase.co",
  SUPABASE_ANON_KEY: "YOUR-ANON-KEY",

  // The single shared fellowship account. Fellows are all given the same
  // password; the email below is only used internally to identify the one
  // Supabase Auth user that everyone shares. It is never shown to users.
  SHARED_EMAIL: "fellows@eamorris.org",

  // ---- Demo mode ----------------------------------------------------------
  // Used only when Supabase is not configured above.
  DEMO_PASSWORD: "eamorris2026",

  // ---- Content ------------------------------------------------------------
  PROGRAM_NAME: "EA Morris Fellowship for Emerging Leaders",
  PROGRAM_SHORT: "Fellowship Portal",
};

/** True when real Supabase credentials have been supplied. */
window.EAM_CONFIG.isLive = function () {
  return (
    !!this.SUPABASE_URL &&
    !!this.SUPABASE_ANON_KEY &&
    !this.SUPABASE_URL.includes("YOUR-PROJECT") &&
    !this.SUPABASE_ANON_KEY.includes("YOUR-ANON-KEY")
  );
};
