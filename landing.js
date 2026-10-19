/**
 * Public landing page behaviour.
 *
 * Reads the `fellows` table directly over Supabase's REST API using the public
 * anon key (the table has a public read policy). No auth library is needed, so
 * this page stays light. Falls back to the bundled sample data when Supabase
 * isn't configured.
 */
(function () {
  const $ = (sel) => document.querySelector(sel);
  const PAGE_SIZE = 24;

  const state = { all: [], filtered: [], shown: 0, q: "", year: "" };

  /* ------------------------------ helpers ------------------------------ */
  function escapeHtml(str) {
    return String(str == null ? "" : str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function initials(name) {
    return String(name || "?")
      .split(/\s+/).filter(Boolean).slice(0, 2)
      .map((w) => w[0].toUpperCase()).join("");
  }

  function excerpt(text, max) {
    const t = (text || "").trim();
    if (t.length <= max) return t;
    const cut = t.slice(0, max);
    const at = cut.lastIndexOf(" ");
    return cut.slice(0, at > 0 ? at : max).replace(/[,;:.\s]+$/, "") + "…";
  }

  /* ------------------------------- data -------------------------------- */
  async function loadFellows() {
    const cfg = window.EAM_CONFIG;
    if (!cfg || !cfg.isLive()) {
      return (window.EAM_DEMO_FELLOWS || []).slice().sort((a, b) =>
        (a.full_name || "").localeCompare(b.full_name || "")
      );
    }
    const cols = "id,full_name,cohort_year,bio,current_company,current_title,headline,industry,city,state,country,linkedin_url";
    const url = `${cfg.SUPABASE_URL}/rest/v1/fellows?select=${cols}&order=full_name.asc`;
    const res = await fetch(url, {
      headers: {
        apikey: cfg.SUPABASE_ANON_KEY,
        Authorization: `Bearer ${cfg.SUPABASE_ANON_KEY}`,
      },
    });
    if (!res.ok) throw new Error(`Fellows request failed (${res.status})`);
    return res.json();
  }

  /* ------------------------------ stats -------------------------------- */
  function renderStats(fellows) {
    const years = fellows.map((f) => f.cohort_year).filter(Boolean);
    const cohorts = new Set(years);
    const favg = $("#statFellows");
    const cavg = $("#statCohorts");
    if (favg) favg.textContent = fellows.length;
    if (cavg) cavg.textContent = cohorts.size;
  }

  /* ----------------------------- rendering ----------------------------- */
  function applyFilters() {
    const q = state.q.toLowerCase();
    state.filtered = state.all.filter((f) => {
      const hay = [f.full_name, f.current_company, f.current_title, f.headline,
        f.industry, f.city, f.state, f.country, f.bio].join(" ").toLowerCase();
      return (!q || hay.includes(q)) &&
        (!state.year || String(f.cohort_year) === state.year);
    });
    state.shown = 0;
    $("#fellowGrid").innerHTML = "";
    renderMore();
  }

  function cardHtml(f) {
    return `
      <article class="fellow-card fellow-card-public" data-id="${escapeHtml(f.id)}" tabindex="0">
        <div class="avatar">${escapeHtml(initials(f.full_name))}</div>
        <div class="fellow-info">
          <h3 class="fellow-name">${escapeHtml(f.full_name)}</h3>
          ${f.cohort_year ? `<p class="fellow-class">Class of ${escapeHtml(f.cohort_year)}</p>` : ""}
          <p class="fellow-bio">${escapeHtml(excerpt(f.bio, 190))}</p>
          <span class="read-more">Read full bio →</span>
        </div>
      </article>`;
  }

  function renderMore() {
    const grid = $("#fellowGrid");
    const next = state.filtered.slice(state.shown, state.shown + PAGE_SIZE);
    grid.insertAdjacentHTML("beforeend", next.map(cardHtml).join(""));
    state.shown += next.length;

    const remaining = state.filtered.length - state.shown;
    const btn = $("#loadMore");
    btn.hidden = remaining <= 0;
    btn.textContent = `Show more fellows (${remaining} remaining)`;
    $("#emptyState").hidden = state.filtered.length !== 0;
    $("#fellowCount").textContent =
      state.filtered.length === state.all.length
        ? `${state.all.length} fellows`
        : `${state.filtered.length} of ${state.all.length}`;
  }

  /* ------------------------------ modal -------------------------------- */
  function openModal(f) {
    const meta = [];
    if (f.cohort_year) meta.push(`Class of ${escapeHtml(f.cohort_year)}`);
    if (f.current_company) meta.push(escapeHtml(f.current_company));
    if (f.city || f.country) meta.push(escapeHtml([f.city, f.state, f.country].filter(Boolean).join(", ")));
    $("#modalBody").innerHTML = `
      <div class="modal-head">
        <div class="avatar avatar-lg">${escapeHtml(initials(f.full_name))}</div>
        <h2>${escapeHtml(f.full_name)}</h2>
        ${meta.length ? `<p class="modal-meta">${meta.join(" · ")}</p>` : ""}
      </div>
      <div class="modal-bio"><p>${escapeHtml(f.bio || "No biography available.")}</p></div>
      ${f.linkedin_url ? `<a class="btn-primary" href="${escapeHtml(f.linkedin_url)}" target="_blank" rel="noopener">Connect on LinkedIn</a>` : ""}`;
    $("#modal").hidden = false;
    $("#modalScrim").hidden = false;
    requestAnimationFrame(() => $("#modal").classList.add("open"));
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    $("#modal").classList.remove("open");
    document.body.style.overflow = "";
    setTimeout(() => { $("#modal").hidden = true; $("#modalScrim").hidden = true; }, 200);
  }

  /* ------------------------------- boot -------------------------------- */
  async function boot() {
    const yr = $("#year");
    if (yr) yr.textContent = new Date().getFullYear();

    let fellows = [];
    try {
      fellows = await loadFellows();
    } catch (err) {
      console.error(err);
      $("#fellowGrid").innerHTML =
        '<p class="empty">Sorry — the fellow directory could not be loaded right now.</p>';
      return;
    }

    state.all = fellows;
    renderStats(fellows);

    // Class-year filter
    const years = Array.from(new Set(fellows.map((f) => f.cohort_year).filter(Boolean)))
      .sort((a, b) => b - a);
    const sel = $("#classYear");
    years.forEach((y) => {
      const o = document.createElement("option");
      o.value = String(y);
      o.textContent = `Class of ${y}`;
      sel.appendChild(o);
    });

    applyFilters();

    // Wire events
    $("#fellowSearch").addEventListener("input", (e) => {
      state.q = e.target.value.trim();
      applyFilters();
    });
    sel.addEventListener("change", (e) => {
      state.year = e.target.value;
      applyFilters();
    });
    $("#loadMore").addEventListener("click", renderMore);

    $("#fellowGrid").addEventListener("click", (e) => {
      const card = e.target.closest(".fellow-card");
      if (!card) return;
      const f = state.all.find((x) => String(x.id) === card.dataset.id);
      if (f) openModal(f);
    });
    $("#fellowGrid").addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      const card = e.target.closest(".fellow-card");
      if (!card) return;
      e.preventDefault();
      const f = state.all.find((x) => String(x.id) === card.dataset.id);
      if (f) openModal(f);
    });

    $("#modalClose").addEventListener("click", closeModal);
    $("#modalScrim").addEventListener("click", closeModal);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !$("#modal").hidden) closeModal();
    });
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
