/**
 * Authentication layer.
 *
 * Live mode  : Supabase Auth with a single shared fellowship account. Every
 *              fellow is given the same password; the account email lives in
 *              config.js and is never exposed in the UI.
 * Demo mode  : No backend. The password from config.js is checked locally and
 *              a session flag is stored in sessionStorage.
 *
 * Exposes window.EAM with login(), logout(), isAuthed(), requireAuth().
 */
(function () {
  const cfg = window.EAM_CONFIG;
  const SESSION_KEY = "eam_session";

  let supabase = null;
  if (cfg.isLive() && window.supabase) {
    supabase = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
  }

  const EAM = {
    live: cfg.isLive(),
    supabase,

    /** Returns true when a valid session is present. */
    async isAuthed() {
      if (this.live) {
        const { data } = await this.supabase.auth.getSession();
        return !!data.session;
      }
      return sessionStorage.getItem(SESSION_KEY) === "1";
    },

    /**
     * Attempt to sign in with the shared password.
     * Resolves on success; throws an Error with a friendly message on failure.
     */
    async login(password) {
      if (this.live) {
        const { error } = await this.supabase.auth.signInWithPassword({
          email: cfg.SHARED_EMAIL,
          password,
        });
        if (error) throw new Error("Incorrect password. Please try again.");
        return;
      }
      // Demo mode
      if (password === cfg.DEMO_PASSWORD) {
        sessionStorage.setItem(SESSION_KEY, "1");
        return;
      }
      throw new Error("Incorrect password. Please try again.");
    },

    async logout() {
      if (this.live) {
        await this.supabase.auth.signOut();
      } else {
        sessionStorage.removeItem(SESSION_KEY);
      }
      window.location.href = "index.html";
    },

    /** Redirect to the login page when there is no session. */
    async requireAuth() {
      if (!(await this.isAuthed())) {
        window.location.replace("index.html");
        return false;
      }
      return true;
    },
  };

  window.EAM = EAM;
})();
