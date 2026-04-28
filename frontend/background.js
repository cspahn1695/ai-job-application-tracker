// API origin: same host when served from FastAPI; fallback for file:// or odd hosts
function apiUrl(path) {
  if (!path.startsWith("/")) path = "/" + path;
  if (window.location.protocol === "file:" || !window.location.host) {
    return "http://127.0.0.1:8000" + path;
  }
  return path;
}

let email = (localStorage.getItem("userEmail") || "").trim().toLowerCase();
if (email) localStorage.setItem("userEmail", email);

function loadBackground() {
  if (!email) return;
  fetch(apiUrl(`/background/${encodeURIComponent(email)}`))
    .then((res) => res.json())
    .then((data) => {
      renderList("skillsList", data.skills, "skills");
      renderList("educationList", data.education, "education");
      renderList("experienceList", data.experience, "experience");
      renderList("savedJobsList", data.saved_jobs || [], "saved_jobs");
    });
}

function renderList(elementId, items, section) {
  const el = document.getElementById(elementId);
  el.innerHTML = "";

  items.forEach((item) => {
    el.innerHTML += `
      <li>
        ${item}
        <button onclick="deleteItem('${section}', '${item}')" class="btn btn-sm btn-danger ms-2">
          X
        </button>
      </li>
    `;
  });
}

function addSkill() {
  addItem("skills", document.getElementById("skillInput").value);
}

function addEducation() {
  addItem("education", document.getElementById("educationInput").value);
}

function addExperience() {
  addItem("experience", document.getElementById("experienceInput").value);
}
function addSavedJob() {
  addItem("saved_jobs", document.getElementById("savedJobInput").value);
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
  fetch(apiUrl("/auth/create-admin"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      new_email: newEmail.trim().toLowerCase(),
      new_password: newPassword,
      admin_email: email,
      admin_password: adminPassword,
    }),
  })
    .then(async (res) => {
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

      if (!Array.isArray(data)) {
        el.innerHTML = "<li>Unexpected response from server.</li>";
        return;
      }

      data.forEach((item) => {
        const job = jobPayloadFromItem(item);
        const title = job.title || "Untitled role";
        const company = job.company || "Company not listed";
        const loc = jobLocationText(job);
        const jobUrl = job.url || "#";
        el.innerHTML += `
          <li class="mb-3 pb-3 border-bottom">
            <div class="fw-bold">${escapeHtml(title)}</div>
            <div class="text-secondary small">${escapeHtml(company)}</div>
            <div class="mt-2"><span class="badge bg-secondary">Location</span> ${escapeHtml(loc)}</div>
            <div class="mt-1"><span class="badge bg-info text-dark">Match</span> ${escapeHtml(String(item.score))}%</div>
            <div class="mt-2"><a class="btn btn-sm btn-outline-primary" href="${escapeHtml(jobUrl)}" target="_blank" rel="noopener noreferrer">View Job</a></div>
            <div class="col-auto">
              <button type="button" onclick="saveJob()" class="btn btn-outline-secondary btn-sm">Save Job</button>
            </div>
          </li>
        `;
      });
    })
    .catch((err) => {
      console.error(err);
      alert("Error fetching jobs");
    });
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
