const email = localStorage.getItem("userEmail");

function loadBackground() {
  if (!email) return;
  fetch(`/background/${email}`)
    .then(res => res.json())
    .then(data => {
      renderList("skillsList", data.skills, "skills");
      renderList("educationList", data.education, "education");
      renderList("experienceList", data.experience, "experience");
    });
}

function renderList(elementId, items, section) {
  const el = document.getElementById(elementId);
  el.innerHTML = "";

  items.forEach(item => {
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

function addItem(section, value) {
  fetch(`/background/${email}/${section}?item=${value}`, {
    method: "POST"
  }).then(loadBackground);
}

function deleteItem(section, value) {
  fetch(`/background/${email}/${section}?item=${value}`, {
    method: "DELETE"
  }).then(loadBackground);
}

function goToApp() {
  window.location.href = "/static/index.html";
}

function loadJobLimitHint() {
  fetch("/settings/max-recommend-jobs")
    .then((res) => res.json())
    .then((data) => {
      const hint = document.getElementById("jobLimitHint");
      if (hint) {
        hint.textContent = `Up to ${data.max_recommend_jobs} jobs will be listed (global limit set by an administrator).`;
        hint.style.display = "block";
      }
      const disp = document.getElementById("maxJobsDisplay");
      if (disp) disp.textContent = data.max_recommend_jobs;
      const inp = document.getElementById("maxJobsInput");
      if (inp) inp.value = data.max_recommend_jobs;
    })
    .catch(() => {});
}

function refreshAdminUi() {
  if (!email) return;
  fetch(`/auth/me?email=${encodeURIComponent(email)}`)
    .then((res) => {
      if (!res.ok) throw new Error("me failed");
      return res.json();
    })
    .then((data) => {
      localStorage.setItem("isAdmin", data.is_admin ? "true" : "false");
      const panel = document.getElementById("adminPanel");
      if (panel) panel.style.display = data.is_admin ? "block" : "none";
    })
    .catch(() => {
      const panel = document.getElementById("adminPanel");
      if (panel) panel.style.display = "none";
    });
}

function saveMaxJobs() {
  const max = parseInt(document.getElementById("maxJobsInput").value, 10);
  const pwd = document.getElementById("adminPasswordConfirm").value;
  if (!pwd) {
    alert("Enter your password to confirm.");
    return;
  }
  fetch("/settings/max-recommend-jobs", {
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
  fetch("/auth/create-admin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      new_email: newEmail,
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

function getJobs() {
  const city = document.getElementById("cityInput").value;

  fetch(`/applications/recommend-jobs/${email}?city=${city}`)
    .then(res => {
      if (!res.ok) throw new Error("Request failed");
      return res.json();
    })
    .then(data => {
      console.log("Jobs:", data);  // 👈 ADD THIS

      const el = document.getElementById("jobResults");
      el.innerHTML = "";

      data.forEach(item => {
        const loc = item.job.location || "Not specified";
        el.innerHTML += `
          <li>
            <b>${item.job.title}</b> (${item.job.company})<br>
            Location: ${loc}<br>
            Match: ${item.score}%<br>
            <a href="${item.job.url}" target="_blank">View Job</a>
          </li>
        `;
      });
    })
    .catch(err => {
      console.error(err);
      alert("Error fetching jobs");
    });
}

window.onload = () => {
  if (!email) {
    window.location.href = "/";
    return;
  }
  loadBackground();
  loadJobLimitHint();
  refreshAdminUi();
};