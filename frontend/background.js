// API origin: pages under /static/ are served by FastAPI — use same origin. Otherwise (e.g. Live
// Server on another port) POSTing to a relative "/applications/" hits the wrong host; match main.js.
function resolveBackendOrigin() {
  if (window.location.protocol === "file:" || !window.location.host) {
    return "http://127.0.0.1:8000";
  }
  const path = window.location.pathname || "";
  if (path.includes("/static/")) {
    return window.location.origin;
  }
  return "http://127.0.0.1:8000";
}

function apiUrl(path) {
  if (!path.startsWith("/")) path = "/" + path;
  return resolveBackendOrigin() + path;
}

/** Headers for authenticated application API calls (same token as My Applications page). */
function applicationApiHeaders() {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem("accessToken");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * "View job" href: Adzuna tracking URLs go through our resolver (one hop when clicked);
 * other URLs open directly. Keeps job search fast (no bulk redirect resolution).
 */
function jobViewHref(rawUrl) {
  const u = (rawUrl || "").trim();
  if (!u || u === "#") {
    return u || "#";
  }
  try {
    const hostname = new URL(u).hostname.toLowerCase();
    if (hostname.includes("adzuna")) {
      return (
        apiUrl("/applications/resolve-listing-url") +
        "?url=" +
        encodeURIComponent(u)
      );
    }
  } catch (e) {
    return u;
  }
  return u;
}

/**
 * POST /applications/ — use same host as the FastAPI app when it serves this UI on port 8000
 * (covers /static/… and default-site paths). Otherwise match main.js fallback host.
 */
function applicationsCreateUrl() {
  if (window.location.protocol === "file:" || !window.location.host) {
    return "http://127.0.0.1:8000/applications/";
  }
  const port = window.location.port || (window.location.protocol === "https:" ? "443" : "80");
  if (port === "8000") {
    return window.location.origin.replace(/\/$/, "") + "/applications/";
  }
  return "http://127.0.0.1:8000/applications/";
}

/** Create a My Applications row (Plan to Apply) from a normalized job object. */
function postJobAsPlanToApplyApplication(job) {
  const token = (localStorage.getItem("accessToken") || "").trim();
  if (!token) {
    return Promise.reject(
      new Error(
        "You need to be signed in. Open My Applications or log in again, then try Save Job."
      )
    );
  }

  const jobUrl = (job.url || "").trim();
  if (!jobUrl) {
    return Promise.reject(new Error("This job is missing a URL, so it can't be saved."));
  }

  const body = {
    company: (job.company || "Company not listed").trim(),
    role: (job.title || "Untitled role").trim(),
    status: "plan_to_apply",
    priority: "medium",
    recruitmentinfo: (jobLocationText(job) || "Not specified").trim(),
    jobpostinglink: jobUrl,
  };

  return fetch(applicationsCreateUrl(), {
    method: "POST",
    headers: applicationApiHeaders(),
    body: JSON.stringify(body),
  }).then(async (res) => {
    const data = await res.json().catch(async () => {
      const text = await res.text().catch(() => "");
      return { detail: text };
    });
    if (res.status < 200 || res.status >= 300) {
      const detail = data.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((x) => x.msg || x).join(" ")
            : detail
              ? JSON.stringify(detail)
              : "Could not add application";
      throw new Error(msg);
    }
    return data;
  });
}

let email = (localStorage.getItem("userEmail") || "").trim().toLowerCase();
if (email) localStorage.setItem("userEmail", email);
let latestRecommendedJobs = [];
/** Jobs from the profile page unified search (see /applications/profile-job-search) */
let latestProfilePageJobs = [];

function loadBackground() {
  if (!email) return;
  fetch(apiUrl(`/background/${encodeURIComponent(email)}`))
    .then((res) => res.json())
    .then((data) => {
      renderList("skillsList", data.skills, "skills");
      renderList("educationList", data.education, "education");
      renderList("experienceList", data.experience, "experience");
      renderSavedJobs(data.saved_jobs || []);
    });
}

function renderList(elementId, items, section) {
  const ul = document.getElementById(elementId);
  ul.innerHTML = "";

  items.forEach((item) => {
    ul.innerHTML += `
      <li class="list-group-item d-flex justify-content-between align-items-center">
        ${item}

        <button class="btn btn-sm btn-outline-danger" onclick="deleteItem('${section}', '${item}')">
          ✕
        </button>
      </li>
    `;
  });
}

function addSkill() {
  addItem("skills", document.getElementById("skillInput").value);
  document.getElementById("skillInput").value = "";

}

function addEducation() {
  addItem("education", document.getElementById("educationInput").value);
  document.getElementById("educationInput").value = "";
}

function addExperience() {
  addItem("experience", document.getElementById("experienceInput").value);
  document.getElementById("experienceInput").value = "";
}

function addItem(section, value) {
  fetch(
    apiUrl(
      `/background/${encodeURIComponent(email)}/${section}?item=${encodeURIComponent(value)}`
    ),
    { method: "POST" }
  ).then(loadBackground);
}

function deleteItem(section, value) {
  fetch(
    apiUrl(
      `/background/${encodeURIComponent(email)}/${section}?item=${encodeURIComponent(value)}`
    ),
    { method: "DELETE" }
  ).then(loadBackground);
}

function goToApp() {
  window.location.href = "/static/index.html";
}

function goToJobs() {
  window.location.href = "/static/search.html";
}

function goToBackground() {
  window.location.href = "/static/background.html";
}

function goToInterviewPrep() {
  window.location.href = "/static/interview.html";
}

function logout() {
  localStorage.removeItem("loggedIn");
  localStorage.removeItem("userEmail");
  localStorage.removeItem("isAdmin");
  localStorage.removeItem("accessToken");

  alert("Logged out");

  window.location.href = "/static/login.html";

}

function renderSavedJobs(items) {
  const el = document.getElementById("savedJobsList");
  if (!el) return;
  el.innerHTML = "";

  if (!Array.isArray(items) || items.length === 0) {
    el.innerHTML = '<li class="text-muted">No saved jobs yet.</li>';
    return;
  }

  items.forEach((job) => {
    const isLegacyString = typeof job === "string";
    const title = isLegacyString
      ? String(job)
      : (job && job.title ? String(job.title) : "Untitled role");
    const url = isLegacyString
      ? ""
      : (job && job.url ? String(job.url) : "");
    const company = isLegacyString
      ? "Saved previously"
      : (job && job.company ? String(job.company) : "Company not listed");
    const location = isLegacyString
      ? "Not specified"
      : (job && job.location ? String(job.location) : "Not specified");
    const actionsHtml = url
      ? `<a class="btn btn-sm btn-outline-primary" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Open Job</a>
         <button type="button" onclick="deleteSavedJob('${encodeURIComponent(url)}')" class="btn btn-sm btn-danger">Remove</button>`
      : `<span class="text-muted small">Legacy entry (no link available)</span>`;

    el.innerHTML += `
      <li class="mb-2 p-2 border rounded">
        <div class="fw-bold">${escapeHtml(title)}</div>
        <div class="text-secondary small">${escapeHtml(company)} | ${escapeHtml(location)}</div>
        <div class="mt-2 d-flex gap-2">
          ${actionsHtml}
        </div>
      </li>
    `;
  });
}

function escapeHtml(s) {
  if (s == null || s === "") return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function jobPayloadFromItem(item) {
  if (!item) return {};
  if (item.job && typeof item.job === "object") return item.job;
  return item;
}

function jobLocationText(job) {
  if (!job) return "Not specified";
  const parts = [
    job.location,
    job.search_city,
    job.location_description,
    job.area,
  ].filter(function (x) {
    return x != null && String(x).trim() !== "";
  });
  if (parts.length) return String(parts[0]).trim();
  return "Not specified";
}

function loadJobLimitHint() {
  const hint = document.getElementById("jobLimitHint");
  if (hint) {
    hint.style.display = "block";
    hint.textContent = "Loading job list limit…";
  }
  fetch(apiUrl("/settings/max-recommend-jobs"))
    .then((res) => {
      if (!res.ok) throw new Error("Could not load settings");
      return res.json();
    })
    .then((data) => {
      const n = data.max_recommend_jobs;
      if (hint) {
        hint.textContent =
          "Everyone (basic users and admins) sees up to " +
          n +
          ' job(s) after clicking “Find Jobs.” Admins can change this below.';
        hint.classList.remove("text-danger");
        hint.classList.add("text-muted");
      }
      const disp = document.getElementById("maxJobsDisplay");
      if (disp) disp.textContent = n;
      const inp = document.getElementById("maxJobsInput");
      if (inp) inp.value = n;
    })
    .catch(() => {
      if (hint) {
        hint.textContent =
          "Could not load the global job limit. Check that the API is running and refresh.";
        hint.classList.add("text-danger");
        hint.classList.remove("text-muted");
      }
    });
}

function refreshAdminUi() {
  if (!email) return;
  const panel = document.getElementById("adminPanel");
  const isAdminCached = localStorage.getItem("isAdmin") === "true";
  if (panel && isAdminCached) {
    panel.style.display = "block";
  }

  fetch(apiUrl(`/auth/me?email=${encodeURIComponent(email)}`))
    .then((res) => {
      if (!res.ok) throw new Error("me failed");
      return res.json();
    })
    .then((data) => {
      localStorage.setItem("isAdmin", data.is_admin ? "true" : "false");
      if (panel) {
        panel.style.display = data.is_admin ? "block" : "none";
      }
    })
    .catch(() => {
      if (panel && !isAdminCached) {
        panel.style.display = "none";
      }
    });
}

function saveMaxJobs() {
  const max = parseInt(document.getElementById("maxJobsInput").value, 10);
  const pwd = document.getElementById("adminPasswordConfirm").value;
  if (!pwd) {
    alert("Enter your password to confirm.");
    return;
  }
  fetch(apiUrl("/settings/max-recommend-jobs"), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      admin_email: email,
      admin_password: pwd,
      max_recommend_jobs: max,
    }),
  })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Save failed");
      return data;
    })
    .then((data) => {
      alert(`Saved. Max jobs is now ${data.max_recommend_jobs}.`);
      document.getElementById("adminPasswordConfirm").value = "";
      loadJobLimitHint();
    })
    .catch((err) => alert(err.message));
}

function createAnotherAdmin() {
  const newEmail = document.getElementById("newAdminEmail").value;
  const newPassword = document.getElementById("newAdminPassword").value;
  const adminPassword = document.getElementById("createAdminPasswordConfirm").value;
  if (!newEmail || !newPassword || !adminPassword) {
    alert("Fill in all fields.");
    return;
  }
  fetch(apiUrl("/auth/create-admin"), { // create a new admin
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      new_email: newEmail.trim().toLowerCase(),
      new_password: newPassword,
      admin_email: email,
      admin_password: adminPassword,
    }),
  })
    .then(async (res) => { // this code is a safe way to extract data from the network. IT ensures the application doesn't crash if the response is not valid JSON.
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Failed");
      return data;
    })
    .then(() => {
      alert("New admin created.");
      document.getElementById("newAdminEmail").value = "";
      document.getElementById("newAdminPassword").value = "";
      document.getElementById("createAdminPasswordConfirm").value = "";
    })
    .catch((err) => alert(err.message));
}

function onJobSearchModeChange() {
  const mode = (document.getElementById("jobSearchModeSelect") || {}).value;
  const titleInput = document.getElementById("jobSearchTitleInput");
  if (!titleInput) return;
  if (mode === "profile") {
    titleInput.disabled = true;
    titleInput.setAttribute("aria-disabled", "true");
    titleInput.placeholder = "Not used for profile-only search";
  } else {
    titleInput.disabled = false;
    titleInput.removeAttribute("aria-disabled");
    titleInput.placeholder = "e.g. software engineer, data analyst";
  }
}

function runProfileJobSearch() {
  const mode = (document.getElementById("jobSearchModeSelect") || {}).value;
  const title = (document.getElementById("jobSearchTitleInput") || {}).value || "";
  const city = (document.getElementById("jobSearchLocationInput") || {}).value || "";
  const trimmedTitle = title.trim();
  const trimmedCity = city.trim();

  if ((mode === "title_location" || mode === "both") && !trimmedTitle) {
    alert(
      "Enter a job title or keywords for this search type. Location is optional."
    );
    return;
  }
  if ((mode === "profile" || mode === "both") && !email) {
    alert("You must be logged in to use profile-based search.");
    return;
  }

  const params = new URLSearchParams();
  params.set("mode", mode);
  params.set("city", trimmedCity);
  if (trimmedTitle) {
    params.set("title", trimmedTitle);
  }
  if (mode === "profile" || mode === "both") {
    params.set("email", email);
  }

  const url = apiUrl("/applications/profile-job-search?" + params.toString());

  fetch(url)
    .then((res) => {
      if (!res.ok) {
        return res.json().then((body) => {
          const msg = body.detail || res.statusText || "Request failed";
          const text =
            typeof msg === "string"
              ? msg
              : Array.isArray(msg)
                ? msg.map((x) => x.msg || x).join(" ")
                : JSON.stringify(msg);
          throw new Error(text);
        });
      }
      return res.json();
    })
    .then((data) => {
      const el = document.getElementById("adzunaJobResults");
      if (!el) return;
      el.innerHTML = "";
      latestProfilePageJobs = [];

      if (!Array.isArray(data)) {
        el.innerHTML = "<div class=\"col-12\">Unexpected response from server.</div>";
        return;
      }

      if (data.length === 0) {
        el.innerHTML =
          '<div class="col-12 text-muted">No jobs returned. Try different keywords or location.</div>';
        return;
      }

      data.forEach((item) => {
        const job = jobPayloadFromItem(item);
        latestProfilePageJobs.push(job);
        const idx = latestProfilePageJobs.length - 1;
        const jtitle = job.title || "Untitled role";
        const company = job.company || "Company not listed";
        const loc = jobLocationText(job);
        const jobUrl = job.url || "#";
        const score = item.score;
        const scoreBadges =
          score != null && score !== ""
            ? `<span class="badge bg-info text-dark">Match score ${escapeHtml(String(score))}%</span>`
            : `<span class="badge bg-light text-dark border">Keyword search</span>`;

        el.innerHTML += `
          <div class="col-md-6 col-lg-4">
            <div class="card h-100 shadow-sm border-0">
              <div class="card-body d-flex flex-column">
                <h5 class="card-title mb-1">${escapeHtml(jtitle)}</h5>
                <div class="text-muted mb-2">at ${escapeHtml(company)}</div>
                <div class="mb-2 d-flex flex-wrap gap-1 align-items-center">
                  <span class="badge bg-secondary">${escapeHtml(loc)}</span>
                  ${scoreBadges}
                </div>
                <div class="flex-grow-1"></div>
                <div class="d-flex gap-2 mt-3">
                  <a class="btn btn-sm btn-outline-primary" href="${jobViewHref(jobUrl)}" target="_blank" rel="noopener noreferrer">View Job</a>
                  <button type="button" onclick="saveProfilePageJob(${idx})" class="btn btn-outline-secondary btn-sm">Save Job</button>
                </div>
              </div>
            </div>
          </div>
        `;
      });
    })
    .catch((err) => {
      console.error(err);
      alert(err.message || "Error fetching jobs");
    });
}

function saveProfilePageJob(index) {
  const job = latestProfilePageJobs[index];
  if (!job) {
    alert("Could not save this job.");
    return;
  }

  postJobAsPlanToApplyApplication(job)
    .then(() => {
      alert("Saved to My Applications as Plan to Apply.");
    })
    .catch((err) => alert(err.message));
}

// function saveJob() {
//   const jobTitle = document.getElementById("jobTitle").value;
//   const jobCompany = document.getElementById("jobCompany").value;
//   const jobLocation = document.getElementById("jobLocation").value;
//   const jobUrl = document.getElementById("jobUrl").value;

//   if (!jobTitle || !jobCompany || !jobLocation || !jobUrl) {
//     alert("Fill in all fields.");
//     return;
//   }

//   fetch(apiUrl("/jobs"), {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify({
//       title: jobTitle,
//       company: jobCompany,
//       location: jobLocation,
//       url: jobUrl,
//     }),
//   })
//     .then(async (res) => {
//       const data = await res.json().catch(() => ({}));
//       if (!res.ok) throw new Error(data.detail || "Failed");
//       return data;
//     })
//     .then(() => {
//       alert("Job saved.");
//       document.getElementById("jobTitle").value = "";
//       document.getElementById("jobCompany").value = "";
//       document.getElementById("jobLocation").value = "";
//       document.getElementById("jobUrl").value = "";
//     })
//     .catch((err) => alert(err.message));
// }

function getJobs() {
  const city = document.getElementById("cityInput").value;

  const url =
    apiUrl("/applications/recommend-jobs/") +
    encodeURIComponent(email) +
    "?city=" +
    encodeURIComponent(city || "");

  fetch(url)
    .then((res) => {
      if (!res.ok) throw new Error("Request failed");
      return res.json();
    })
    .then((data) => {
      const el = document.getElementById("jobResults");
      el.innerHTML = "";
      latestRecommendedJobs = [];

      if (!Array.isArray(data)) {
        el.innerHTML = "<div>Unexpected response from server.</div>";
        return;
      }

      data.forEach((item) => {
        const job = jobPayloadFromItem(item);
        latestRecommendedJobs.push(job);
        const idx = latestRecommendedJobs.length - 1;
        const title = job.title || "Untitled role";
        const company = job.company || "Company not listed";
        const loc = jobLocationText(job);
        const jobUrl = job.url || "#";
        el.innerHTML += `
          <div class="col-md-6 col-lg-4">
            <div class="card h-100 shadow-sm border-0">
              <div class="card-body d-flex flex-column">
                <h5 class="card-title mb-1">${escapeHtml(title)}</h5>
                <div class="text-muted mb-2">at ${escapeHtml(company)}</div>
                
                <div class="mb-2">
                  <span class="badge bg-secondary me-1"> ${escapeHtml(loc)} </span>
                  <span class="badge bg-info text-dark">Match Score ${escapeHtml(String(item.score))}%</span>
                </div>

                <div class="flex-grow-1"></div>
                
                <div class="d-flex gap-2 mt-3">
                  <a class="btn btn-sm btn-outline-primary" href="${jobViewHref(jobUrl)}" target="_blank" rel="noopener noreferrer">View Job</a>
                  <button onclick="saveRecommendedJob(${idx})" class="btn btn-outline-secondary btn-sm">Save Job</button>
                </div>
              </div>
            </div>
          </div>
        `;
      });
    })
    .catch((err) => {
      console.error(err);
      alert("Error fetching jobs");
    });
}

function saveRecommendedJob(index) {
  const job = latestRecommendedJobs[index];
  if (!job) {
    alert("Could not save this job.");
    return;
  }

  const payload = {
    title: (job.title || "Untitled role").trim(),
    url: (job.url || "").trim(),
    company: (job.company || "Company not listed").trim(),
    location: (jobLocationText(job) || "Not specified").trim(),
  };

  if (!payload.url) {
    alert("This job is missing a URL, so it can't be saved.");
    return;
  }

  fetch(apiUrl(`/background/${encodeURIComponent(email)}/saved-jobs/item`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then(async (res) => {
      const data = await res.json().catch(async () => {
        const text = await res.text().catch(() => "");
        return { detail: text };
      });
      if (!res.ok) throw new Error(data.detail || "Could not save job");
      return data;
    })
    .then(() => {
      loadBackground();
      alert("Job saved.");
    })
    .catch((err) => alert(err.message));
}

function deleteSavedJob(encodedUrl) {
  const url = decodeURIComponent(encodedUrl || "");
  fetch(
    apiUrl(`/background/${encodeURIComponent(email)}/saved-jobs/item?url=${encodeURIComponent(url)}`),
    { method: "DELETE" }
  )
    .then(async (res) => {
      const data = await res.json().catch(async () => {
        const text = await res.text().catch(() => "");
        return { detail: text };
      });
      if (!res.ok) throw new Error(data.detail || "Could not remove job");
      return data;
    })
    .then(() => loadBackground())
    .catch((err) => alert(err.message));
}

function toggleDropdown() {                
  const el = document.getElementById("myDropdown");
  const arrow = document.getElementById("arrow");

  el.classList.toggle("show");
  arrow.textContent = el.classList.contains("show") ? "▲" : "▼";
}

window.onload = () => {
  email = (localStorage.getItem("userEmail") || "").trim().toLowerCase();
  if (email) localStorage.setItem("userEmail", email);

  if (!email) {
    window.location.href = "/";
    return;
  }
  loadBackground();
  loadJobLimitHint();
  refreshAdminUi();
};
