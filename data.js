/**
 * Data access layer.
 *
 * Live mode : reads the `jobs` and `fellows` tables from Supabase.
 * Demo mode : reads the bundled sample data in demo-data.js.
 *
 * Both paths return arrays of identically-shaped objects, so the UI never has
 * to know which mode it is running in.
 */
window.EAMData = (function () {
  const configured = window.EAM && window.EAM.live;

  async function fromSupabase(table) {
    const supabase = window.EAM.supabase;
    const { data, error } = await supabase
      .from(table)
      .select("*")
      .order(table === "jobs" ? "posted_at" : "full_name", {
        ascending: table !== "jobs",
      });
    if (error) {
      console.error("Supabase error for " + table + ":", error.message);
      return [];
    }
    return data || [];
  }

  return {
    async getJobs() {
      const jobs = configured ? await fromSupabase("jobs") : window.EAM_DEMO_JOBS;
      return jobs.slice().sort((a, b) => (a.posted_at < b.posted_at ? 1 : -1));
    },
    async getFellows() {
      const fellows = configured
        ? await fromSupabase("fellows")
        : window.EAM_DEMO_FELLOWS;
      return fellows.slice().sort((a, b) =>
        (a.full_name || "").localeCompare(b.full_name || "")
      );
    },
  };
})();
