/*
function checkAuth() {
  const loggedIn = localStorage.getItem("loggedIn");

  const loginView = document.getElementById("loginView");
  const appView = document.getElementById("appView");

  if (loggedIn) {
    loginView.style.display = "none";
    appView.style.display = "block";

    const email = localStorage.getItem("userEmail");
    document.getElementById("userInfo").innerText = "Logged in as: " + email;

    getAllApplications();
  } else {
    loginView.style.display = "flex";
    appView.style.display = "none";
  }
}
  */

function checkAuth() {
  const loggedIn = localStorage.getItem("loggedIn") === "true";
  const path = window.location.pathname;
  const isLoginPage = path === "/" || path.endsWith("/login.html");
  const isAppPage = path.endsWith("/index.html");

  // Keep login page separate: signed-in users go directly to app page.
  if (isLoginPage) {
    if (loggedIn) {
      window.location.href = "/static/index.html";
    }
    return;
  }

  // Guard app page: users must be signed in to view it.
  if (isAppPage) {
    if (!loggedIn) {
      window.location.href = "/";
      return;
    }

    const appView = document.getElementById("appView");
    if (appView) {
      appView.style.display = "block";
    }

    const email = localStorage.getItem("userEmail");
    const userInfo = document.getElementById("userInfo");
    if (userInfo) {
      userInfo.innerText = "Logged in as: " + email;
    }

    getAllApplications();
  }
}

// run on load
window.onload = checkAuth;
// used ChatGPT to help write this code; added comments where appropriate.

function applyAuthHeader(xhr) {
  const token = localStorage.getItem("accessToken");
  if (token) {
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
  }
}

function renderApplications(data) {
  const appDiv = document.getElementById('todos');
  appDiv.innerHTML = '';
  
  data.forEach((x) => {
    appDiv.innerHTML += `
    <div class="card mb-3 shadow-sm" id="app-${x._id}">
      <div class="card-body">
        <!-- HEADER -->
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <h5 class="card-title mb-0">${x.role}</h5>
            <div class="text-muted">at ${x.company}</div>
          </div>
          <span class="badge bg-${
              x.status === 'offer' ? 'success' :
              x.status === 'interview' ? 'warning' :
              x.status === 'rejected' ? 'danger' :
              'secondary'
            }"> 
              ${x.status}
          </span>
        </div>

        <!-- BODY -->
        <div class="mt-3">
          <div><strong>Priority:</strong> ${x.priority}</div>
          <div><strong>Recruitment Info:</strong> ${x.recruitmentinfo}</div>
          <div><strong>Job Posting:</strong> <a href="${x.jobpostinglink}" target="_blank">${x.jobpostinglink}</a></div>
          <div class="mt-2">
            ${x.resume_path ? 
              `<a href="http://127.0.0.1:8000/${x.resume_path}" target="_blank" class="btn btn-sm btn-primary">
                  View Resume
              </a>` 
              : 
              `<span class="text-muted">No Resume</span>`
            }
            ${x.jobpostinglink
              ? `<a href="${x.jobpostinglink}" target="_blank" class="btn btn-sm btn-outline-secondary ms-2">
                  View Job Posting
              </a>`
              : `<span class="text-muted ms-2">No Job Posting Link</span>`
            }

          </div>
        </div>
        
        <button onclick="deleteApplication('${x._id}')" class="btn btn-sm btn-danger mt-2">Delete</button>

        <button onclick="editApplication('${x._id}')" class="btn btn-sm btn-primary mt-2">
        Edit
        </button>

        <button onclick="getMatchScore('${x._id}')" class="btn btn-sm btn-warning mt-2">
        AI Match Score
        </button>
      </div>
    </div>
    `;
  });
}

function getAllApplications() { // using an XMLHttpRequest, if xhr.status=200, obtain all applications from backend (and display them), and display statistics  
  
  // NEW FEATURE: read search + filter values from UI
  const companySearch = document.getElementById("searchCompany")?.value || "";
  const statusFilter = document.getElementById("filterStatus")?.value || "";

  const xhr = new XMLHttpRequest();

  xhr.onload = () => { // if communication is established with backend, update charts on website and update parameters
    if (xhr.status == 200) {
      const data = JSON.parse(xhr.response) || [];
      renderApplications(data);
      updateStatistics(data);
    }
  };

  // NEW FEATURE: dynamically build API query string. If a user searches by status and/or company, make sure to include these.
  let url = "http://127.0.0.1:8000/applications?";

  if (companySearch) {
    url += `company=${companySearch}&`;
  }

  if (statusFilter) {
    url += `status=${statusFilter}`;
  }

  xhr.open('GET', url, true);
  applyAuthHeader(xhr);
  xhr.send(); // send an HTTP request to the backend server (FASTAPI) at the URL specified in the xhr.open() method
}

function deleteApplication(id) {
  const xhr = new XMLHttpRequest();

  xhr.onload = () => {
    if (xhr.status === 200) {
      getAllApplications();
    } else {
      console.error("Delete failed:", xhr.response);
      alert("Delete failed");
    }
  };

  xhr.open('DELETE', `http://127.0.0.1:8000/applications/${id}`, true);
  applyAuthHeader(xhr);
  xhr.send();
}

// NEW FEATURE: edit an existing job application
let currentEditId = null;
function editApplication(id) {

  // find current application info from DOM
  const appDiv = document.getElementById(`app-${id}`);

  const role = appDiv.querySelector(".card-title").innerText;
  const company = appDiv.querySelector(".text-muted").innerText.slice(3);

  document.getElementById("editCompany").value = company;
  document.getElementById("editRole").value = role;

  currentEditId = id;

  const modal = new bootstrap.Modal(document.getElementById("editModal"));
  modal.show();

  const xhr = new XMLHttpRequest();

  xhr.onload = () => {
    if (xhr.status === 200) {
      getAllApplications();
    } else {
      console.error("Edit failed:", xhr.response);
      alert("Edit failed");
    }
  };

}

function saveEdit() {
  const role = document.getElementById("editRole").value;
  const company = document.getElementById("editCompany").value;
  const status = document.getElementById("editStatus").value;
  const priority = document.getElementById("editPriority").value;
  const recruitmentinfo = document.getElementById("editRecruitment").value;
  const jobpostinglink = document.getElementById("editJobLink").value;

  const xhr = new XMLHttpRequest();

  xhr.onload = () => {
    if (xhr.status === 200) {
      getAllApplications();

      // Close modal
      const modalEl = document.getElementById('editModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      modal.hide();
    } else {
      console.error("Edit failed:", xhr.response);
      alert("Edit failed");
    }
  };

  xhr.open("PUT", `http://127.0.0.1:8000/applications/${currentEditId}`, true);
  xhr.setRequestHeader("Content-Type", "application/json");
  applyAuthHeader(xhr);

  xhr.send(JSON.stringify({
    company,
    role,
    status,
    priority,
    recruitmentinfo,
    jobpostinglink
  }));
}

function createApplication() { // to create an application, define all below parameters (but recruitmentinfo, resumeFile, and jobpostinglink are optional)
  const company = document.getElementById("company").value; // get all these values from the backend
  const role = document.getElementById("role").value;
  const status = document.getElementById("status").value;
  const priority = document.getElementById("priority").value;
  const recruitmentinfo = document.getElementById("recruitmentinfo").value;
  const resumeFile = document.getElementById("resume").files[0];
  const jobpostinglink = document.getElementById("jobpostinglink").value;


  const xhr = new XMLHttpRequest();
  xhr.onload = () => {
    if (xhr.status !== 200) {
      console.error("Create failed:", xhr.response);
      alert("Create failed");
      return;
    }

    const app = JSON.parse(xhr.response);

    if (resumeFile) {
      uploadResume(app._id, resumeFile);  // send resume (to backend) using xhr
    }

    getAllApplications(); // refresh application list
  };

  xhr.open("POST", "http://127.0.0.1:8000/applications/", true);
  xhr.setRequestHeader("Content-Type", "application/json");
  applyAuthHeader(xhr);
  xhr.send(
    JSON.stringify({ // send all this data to the backend to create a new application
      company, 
      role, 
      status,
      priority,
      recruitmentinfo,
      jobpostinglink
     })
    );
}

// an XMLHttpRequest (XHR) is used by the frontend (client) to send info to the backend (server) and receive info back

function uploadResume(appId, file) {
  const formData = new FormData();
  formData.append("file", file); // add file to formData

  const xhr = new XMLHttpRequest(); // communicate with backend

  xhr.open("POST", `http://127.0.0.1:8000/applications/${appId}/resume`, true);
  applyAuthHeader(xhr);
  xhr.send(formData); // send resume to backend for application at appId to backend
}


function getMatchScore(appId) { // get scores from backend and send to website

  const xhr = new XMLHttpRequest();

  xhr.onload = () => {
    if (xhr.status !== 200) {
      console.error("Match error:", xhr.response);
      alert("Error getting match score");
      return;
    }

    const result = JSON.parse(xhr.response); // get match score from backend  and display it on website

    // NEW FEATURE: show match score + skill analysis

    const matched = result.matched_skills.join(", ") || "None"; // get these values from backend
    const missing = result.missing_skills.join(", ") || "None";

    alert(
      "AI Match Score: " + result.match_score + "%\n\n" + // print AI match score, matched skills, and missing skills
      "Matched Skills:\n" + matched + "\n\n" +
      "Missing Skills:\n" + missing
    );
  }; 

  xhr.open("GET", `http://127.0.0.1:8000/applications/${appId}/match`, true);
  applyAuthHeader(xhr);
  xhr.send(); // send the match score, matched skills, and missing skills to frontend
}



let statusChart; // define variables for charts/plots on main website
let priorityChart;

function updateStatistics(data) { // called by fxn getAllApplications()

  const total = data.length;

  const statusCounts = { // initialize status (applied, offer, rejected, interview) counts to 0 since initially there are no job apps
    applied: 0,
    interview: 0,
    rejected: 0,
    offer: 0
  };

  const priorityCounts = { // initialize prioritycounts (high, medium, low) to 0 since initially there are no job apps
    high: 0,
    medium: 0,
    low: 0
  };

  data.forEach(app => {
    if (statusCounts[app.status] !== undefined) {
      statusCounts[app.status]++; // whenever you make a new job, it must have a status, so one of the status categories must be incremented
    }

    if (priorityCounts[app.priority] !== undefined) {
      priorityCounts[app.priority]++; // whenever you make a new job, it must have a priority, so one of the priority categories must be incremented
    }
  });

  const interviewRate = total ? ((statusCounts.interview / total) * 100).toFixed(1) : 0; // calculate interview and offer rates based off statuscounts data (ok to do this in the frontend)
  const offerRate = total ? ((statusCounts.offer / total) * 100).toFixed(1) : 0;

  document.getElementById("totalApps").innerText = total; // print these values to frontend
  document.getElementById("interviewRate").innerText = interviewRate + "%";
  document.getElementById("offerRate").innerText = offerRate + "%";

  renderStatusChart(statusCounts); // create charts with statusCounts and priorityCounts and put them on frontend
  renderPriorityChart(priorityCounts);
}






function renderStatusChart(statusCounts) { // put a status chart on the frontend

  const ctx = document.getElementById("statusChart");

  if (statusChart) statusChart.destroy();

  statusChart = new Chart(ctx, {
    type: "bar", // create a bar graph, with 4 columns showing total number of apps in each status category
    data: {
      labels: ["Applied", "Interview", "Rejected", "Offer"], // all columns are blue for now
      datasets: [{
        label: "Applications by Status",
        data: [ 
          statusCounts.applied,
          statusCounts.interview,
          statusCounts.rejected,
          statusCounts.offer
        ]
      }]
    }
  });
}


function renderPriorityChart(priorityCounts) { // put a pie graph on the frontend, showing proportions of high, medium, and low applications

  const ctx = document.getElementById("priorityChart");

  if (priorityChart) priorityChart.destroy();

  priorityChart = new Chart(ctx, { // create a pie graph, with 3 possible sections showing total number of apps in each priority category
    type: "pie",
    data: {
      labels: ["High", "Medium", "Low"], // different colors are used for these 3 categories
      datasets: [{
        label: "Priority Distribution",
        data: [
          priorityCounts.high,
          priorityCounts.medium,
          priorityCounts.low
        ]
      }]
    }
  });
}


function register() { // handles user registration by sending email and password to backend, and if successful, logging the user in
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  fetch("http://127.0.0.1:8000/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ email, password })
  })
  .then(async res => {
    const data = await res.json();
    console.log("REGISTER RESPONSE:", data); // 👈 ADD THIS

    if (!res.ok) {
      // ✅ show real backend error
      throw new Error(data.detail || "Registration failed");
    }

    return data;
  })
  .then(data => {
    alert("Account created! Logging you in...");
    login(); // reuse login function
  })
  .catch(err => alert(err.message));
}



function login() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  fetch("http://127.0.0.1:8000/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ email, password })
  })
  .then(res => {
    if (!res.ok) throw new Error("Invalid login");
    return res.json();
  })
  .then(data => {
    // ✅ STORE LOGIN STATE (email normalized so /auth/me and Background lookups match MongoDB)
    const normalizedEmail = (email || "").trim().toLowerCase();
    localStorage.setItem("loggedIn", "true");
    localStorage.setItem("userEmail", normalizedEmail);
    localStorage.setItem("isAdmin", data.is_admin ? "true" : "false");
    localStorage.setItem("accessToken", data.access_token || "");

    alert("Login successful");

    window.location.href = "/static/index.html";// switch view instead of redirect

  })
  .catch(err => alert(err.message));
}

function logout() {
  localStorage.removeItem("loggedIn");
  localStorage.removeItem("userEmail");
  localStorage.removeItem("isAdmin");
  localStorage.removeItem("accessToken");

  alert("Logged out");

  window.location.href = "/static/login.html";

}

// Admin bootstrap is handled by auth_bootstrap.js (loaded after this file on login pages).

function goToBackground() {
  window.location.href = "/static/background.html";
}

function goToApp() {
  window.location.href = "/static/index.html";
}

function goToJobs() {
  window.location.href = "/static/search.html";
}