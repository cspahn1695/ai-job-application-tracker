function apiBase() {
  if (window.location.protocol === "file:" || !window.location.host) {
    return "http://127.0.0.1:8000";
  }
  return window.location.origin;
}

function authHeaders() {
  const headers = {};
  const token = localStorage.getItem("accessToken");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

function goToApp() {
  window.location.href = "/static/index.html";
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
  window.location.href = "/static/login.html";
}

function escapeHtml(s) {
  if (s == null || s === "") return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderInterviewPrep(items) {
  const root = document.getElementById("interviewPrepList");
  if (!root) return;
  root.innerHTML = "";

  if (!Array.isArray(items) || items.length === 0) {
    root.innerHTML = '<div class="col-12 text-muted">No applications with job posting links yet.</div>';
    return;
  }

  items.forEach((item) => {
    const questions = Array.isArray(item.questions) ? item.questions.slice(0, 6) : [];
    const qHtml = questions.length
      ? `<ol class="mb-0">${questions.map((q) => `<li class="mb-1">${escapeHtml(q)}</li>`).join("")}</ol>`
      : '<div class="text-muted">No questions generated for this posting yet.</div>';
    root.innerHTML += `
      <div class="col-12">
        <div class="card shadow-sm border-0">
          <div class="card-body">
            <h5 class="card-title mb-1">${escapeHtml(item.role || "Untitled role")}</h5>
            <div class="text-muted mb-2">at ${escapeHtml(item.company || "Company not listed")}</div>
            <div class="small mb-3">
              <a href="${escapeHtml(item.jobpostinglink || "#")}" target="_blank" rel="noopener noreferrer">Job posting link</a>
            </div>
            <h6 class="mb-2">Interview questions</h6>
            ${qHtml}
          </div>
        </div>
      </div>
    `;
  });
}

function loadInterviewPrep() {
  const url = apiBase() + "/applications/interview-prep";
  fetch(url, { headers: authHeaders() })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Could not load interview prep");
      }
      return data;
    })
    .then(renderInterviewPrep)
    .catch((err) => {
      alert(err.message || "Could not load interview prep");
    });
}

window.onload = () => {
  const loggedIn = localStorage.getItem("loggedIn") === "true";
  if (!loggedIn) {
    window.location.href = "/";
    return;
  }
  loadInterviewPrep();
}
