/**
 * Portal behaviour: tab switching, filtering, rendering, and the fellow
 * detail drawer. Data is supplied by EAMData (Supabase in live mode, bundled
 * sample data in demo mode).
 */
(function () {
  const $ = (sel) => document.querySelector(sel);

  /* ----------------------------- helpers ------------------------------- */
  function escapeHtml(str) {
    return String(str == null ? "" : str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function initials(name) {
    return String(name || "?")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0].toUpperCase())
      .join("");
  }

  function fellowLocation(f) {
    if (f.city && f.state) return `${f.city}, ${f.state}`;
    return f.city || f.state || f.country || null;
  }

  function formatDate(d) {
    if (!d) return "";
    const dt = new Date(d);
    if (isNaN(dt)) return d;
    return dt.toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
    });
  }

  function uniq(values) {
    return Array.from(new Set(values.filter(Boolean))).sort();
  }

  function fillSelect(select, values, allLabel) {
    const current = select.value;
    select.innerHTML = `<option value="">${allLabel}</option>`;
    values.forEach((v) => {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = v;
      select.appendChild(o);
    });
    if (values.includes(current)) select.value = current;
  }

  /* ------------------------------ state -------------------------------- */
  const state = {
    jobs: [],
    fellows: [],
    jobFilters: { q: "", category: "", type: "", location: "" },
    fellowFilters: { q: "", industry: "", cohort: "", location: "" },
  };

  /* ------------------------------ jobs --------------------------------- */
  function renderJobs() {
    const f = state.jobFilters;
    const q = f.q.toLowerCase();
    const list = state.jobs.filter((j) => {
      const hay = [j.title, j.company, j.description, j.location, (j.tags || []).join(" ")]
        .join(" ")
        .toLowerCase();
      return (
        (!q || hay.includes(q)) &&
        (!f.category || j.category === f.category) &&
        (!f.type || j.work_type === f.type) &&
        (!f.location || j.location === f.location)
      );
    });

    $("#jobsCount").textContent = `${list.length} role${list.length === 1 ? "" : "s"}`;
    const wrap = $("#jobsList");

    if (!list.length) {
      wrap.innerHTML = "";
      toggleEmpty(true);
      return;
    }
    toggleEmpty(false);

    wrap.innerHTML = list
      .map(
        (j) => `
      <article class="job-card${j.featured ? " featured" : ""}">
        ${j.featured ? '<span class="ribbon">Featured</span>' : ""}
        <div class="job-top">
          <div class="job-mark">${escapeHtml(initials(j.company))}</div>
          <div>
            <h3 class="job-title">${escapeHtml(j.title)}</h3>
            <p class="job-company">${escapeHtml(j.company)}</p>
          </div>
        </div>
        <p class="job-desc">${escapeHtml(j.description)}</p>
        <div class="chips">
          <span class="chip chip-solid">${escapeHtml(j.location)}</span>
          <span class="chip">${escapeHtml(j.work_type)}</span>
          <span class="chip">${escapeHtml(j.category)}</span>
        </div>
        <div class="job-foot">
          <span class="job-date">Posted ${escapeHtml(formatDate(j.posted_at))}</span>
          <a class="btn-small" href="${escapeHtml(j.url)}" target="_blank" rel="noopener">View role →</a>
        </div>
      </article>`
      )
      .join("");
  }

  /* ----------------------------- fellows ------------------------------- */
  function fellowHaystack(f) {
    return [
      f.full_name, f.current_company, f.current_title, f.headline,
      f.city, f.state, f.country, f.industry, f.education,
      (f.skills || []).join(" "),
    ].join(" ").toLowerCase();
  }

  function renderFellows() {
    const f = state.fellowFilters;
    const q = f.q.toLowerCase();
    const list = state.fellows.filter((x) => {
      return (
        (!q || fellowHaystack(x).includes(q)) &&
        (!f.industry || x.industry === f.industry) &&
        (!f.cohort || String(x.cohort_year) === f.cohort) &&
        (!f.location || fellowLocation(x) === f.location)
      );
    });

    $("#fellowsCount").textContent = `${list.length} fellow${list.length === 1 ? "" : "s"}`;
    const wrap = $("#fellowsList");

    if (!list.length) {
      wrap.innerHTML = "";
      toggleEmpty(true);
      return;
    }
    toggleEmpty(false);

    wrap.innerHTML = list
      .map((x) => {
        const loc = fellowLocation(x);
        const chips = [];
        if (loc) chips.push(`<span class="chip chip-solid">${escapeHtml(loc)}</span>`);
        if (x.cohort_year) chips.push(`<span class="chip">Cohort ${escapeHtml(x.cohort_year)}</span>`);
        if (x.industry) chips.push(`<span class="chip">${escapeHtml(x.industry)}</span>`);
        const sub = x.headline || x.current_title || x.current_company || "";
        return `
      <article class="fellow-card" data-id="${escapeHtml(x.id)}" tabindex="0">
        <div class="avatar">${escapeHtml(initials(x.full_name))}</div>
        <div class="fellow-info">
          <h3 class="fellow-name">${escapeHtml(x.full_name)}</h3>
          ${sub ? `<p class="fellow-title">${escapeHtml(sub)}</p>` : ""}
          ${
            x.current_company && sub !== x.current_company
              ? `<p class="fellow-company">${escapeHtml(x.current_company)}</p>`
              : ""
          }
          ${chips.length ? `<div class="chips">${chips.join("")}</div>` : ""}
        </div>
      </article>`;
      })
      .join("");
  }

  /* ----------------------------- drawer -------------------------------- */
  function openDrawer(f) {
    $("#drawerBody").innerHTML = `
      <div class="drawer-head">
        <div class="avatar avatar-lg">${escapeHtml(initials(f.full_name))}</div>
        <h2>${escapeHtml(f.full_name)}</h2>
        ${
          f.headline || f.current_title
            ? `<p class="fellow-title">${escapeHtml(f.headline || f.current_title)}</p>`
            : ""
        }
        ${f.current_company ? `<p class="fellow-company">${escapeHtml(f.current_company)}</p>` : ""}
      </div>
      <dl class="detail-list">
        ${f.cohort_year ? `<div><dt>Cohort</dt><dd>${escapeHtml(f.cohort_year)}</dd></div>` : ""}
        <div><dt>Industry</dt><dd>${escapeHtml(f.industry || "—")}</dd></div>
        <div><dt>Location</dt><dd>${escapeHtml(fellowLocation(f) || "—")}</dd></div>
        <div><dt>Education</dt><dd>${escapeHtml(f.education || "—")}</dd></div>
      </dl>
      ${
        (f.skills || []).length
          ? `<div class="drawer-block"><h4>Focus areas</h4><div class="chips">${f.skills
              .map((s) => `<span class="chip">${escapeHtml(s)}</span>`)
              .join("")}</div></div>`
          : ""
      }
      ${f.bio ? `<div class="drawer-block"><h4>About</h4><p>${escapeHtml(f.bio)}</p></div>` : ""}
      <div class="drawer-actions">
        ${
          f.linkedin_url
            ? `<a class="btn-primary" href="${escapeHtml(f.linkedin_url)}" target="_blank" rel="noopener">Connect on LinkedIn</a>`
            : ""
        }
        ${
          f.email
            ? `<a class="btn-ghost" href="mailto:${escapeHtml(f.email)}">Email</a>`
            : ""
        }
      </div>`;
    $("#drawer").hidden = false;
    $("#drawerScrim").hidden = false;
    requestAnimationFrame(() => $("#drawer").classList.add("open"));
  }

  function closeDrawer() {
    const d = $("#drawer");
    d.classList.remove("open");
    setTimeout(() => {
      d.hidden = true;
      $("#drawerScrim").hidden = true;
    }, 220);
  }

  function toggleEmpty(show) {
    $("#emptyState").hidden = !show;
  }

  /* --------------------------- tab switching --------------------------- */
  function setupTabs() {
    document.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((t) => {
          t.classList.toggle("active", t === tab);
          t.setAttribute("aria-selected", t === tab ? "true" : "false");
        });
        const name = tab.dataset.tab;
        $("#panel-jobs").classList.toggle("active", name === "jobs");
        $("#panel-fellows").classList.toggle("active", name === "fellows");
        toggleEmpty(false);
        // Deep-link via hash so refreshes keep the tab.
        history.replaceState(null, "", "#" + name);
      });
    });

    const initial = (location.hash || "").replace("#", "");
    if (initial === "fellows") {
      document.querySelector('.tab[data-tab="fellows"]').click();
    }
  }

  /* ------------------------------ boot --------------------------------- */
  async function boot() {
    // Auth gate
    if (!(await EAM.requireAuth())) return;

    $("#gate").hidden = true;
    $("#app").hidden = false;
    $("#year").textContent = new Date().getFullYear();
    $("#modePill").textContent = EAM.live ? "Live" : "Demo";
    $("#modePill").classList.toggle("live", EAM.live);

    $("#logoutBtn").addEventListener("click", () => EAM.logout());
    document.getElementById("drawerClose").addEventListener("click", closeDrawer);
    document.getElementById("drawerScrim").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !$("#drawer").hidden) closeDrawer();
    });

    setupTabs();

    // Load data
    const [jobs, fellows] = await Promise.all([
      EAMData.getJobs(),
      EAMData.getFellows(),
    ]);
    state.jobs = jobs;
    state.fellows = fellows;

    // Populate filters
    fillSelect($("#jobCategory"), uniq(jobs.map((j) => j.category)), "All categories");
    fillSelect($("#jobType"), uniq(jobs.map((j) => j.work_type)), "All types");
    fillSelect($("#jobLocation"), uniq(jobs.map((j) => j.location)), "All locations");
    fillSelect($("#fellowIndustry"), uniq(fellows.map((f) => f.industry)), "All industries");
    fillSelect(
      $("#fellowCohort"),
      uniq(fellows.map((f) => f.cohort_year)).sort((a, b) => b - a),
      "All cohorts"
    );
    fillSelect($("#fellowLocation"), uniq(fellows.map(fellowLocation)), "All locations");

    // Wire filters
    $("#jobSearch").addEventListener("input", (e) => {
      state.jobFilters.q = e.target.value.trim();
      renderJobs();
    });
    $("#jobCategory").addEventListener("change", (e) => { state.jobFilters.category = e.target.value; renderJobs(); });
    $("#jobType").addEventListener("change", (e) => { state.jobFilters.type = e.target.value; renderJobs(); });
    $("#jobLocation").addEventListener("change", (e) => { state.jobFilters.location = e.target.value; renderJobs(); });

    $("#fellowSearch").addEventListener("input", (e) => {
      state.fellowFilters.q = e.target.value.trim();
      renderFellows();
    });
    $("#fellowIndustry").addEventListener("change", (e) => { state.fellowFilters.industry = e.target.value; renderFellows(); });
    $("#fellowCohort").addEventListener("change", (e) => { state.fellowFilters.cohort = e.target.value; renderFellows(); });
    $("#fellowLocation").addEventListener("change", (e) => { state.fellowFilters.location = e.target.value; renderFellows(); });

    // Fellow card clicks
    $("#fellowsList").addEventListener("click", (e) => {
      const card = e.target.closest(".fellow-card");
      if (card) {
        const f = state.fellows.find((x) => String(x.id) === card.dataset.id);
        if (f) openDrawer(f);
      }
    });
    $("#fellowsList").addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        const card = e.target.closest(".fellow-card");
        if (card) {
          e.preventDefault();
          const f = state.fellows.find((x) => String(x.id) === card.dataset.id);
          if (f) openDrawer(f);
        }
      }
    });

    renderJobs();
    renderFellows();
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
