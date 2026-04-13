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
  const loginView = document.getElementById("loginView");
  const appView = document.getElementById("appView");

  // ✅ If elements don't exist, do nothing
  if (!loginView || !appView) return;

  const loggedIn = localStorage.getItem("loggedIn");

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

// run on load
window.onload = checkAuth;
// used ChatGPT to help write this code; added comments where appropriate.
function renderApplications(data) {
  const appDiv = document.getElementById('todos');
  appDiv.innerHTML = '';
  
  data.forEach((x) => { // load main job app parameters like company, role, status, priority, recruitmentinfo, etc
    appDiv.innerHTML += `
    <div id="app-${x.id}" class="todo-box">
        <div class="fw-bold fs-4">${x.company}</div> 
        <div class="ps-3">Role: ${x.role}</div>
        <div class="ps-3">Status: ${x.status}</div>
        <div class="ps-3">Priority: ${x.priority}</div>
        <div class="ps-3">Recruitment Info: ${x.recruitmentinfo}</div>
        <div class="ps-3">
        <div class="ps-3 mt-2">
        ${x.resume_path ? 
          `<a href="http://127.0.0.1:8000/${x.resume_path}" target="_blank" class="btn btn-sm btn-primary">
              View Resume
          </a>` 
          : 
          `<span class="text-muted">No Resume</span>`
        }
        </div>
        <div class="ps-3">JobPostingLink: ${x.jobpostinglink}</div>
        
        <button onclick="deleteApplication(${x.id})" class="btn btn-sm btn-danger mt-2">Delete</button>

        <!-- NEW FEATURE: edit button allows modifying an existing application -->
        <button onclick="editApplication(${x.id})" class="btn btn-sm btn-primary mt-2">
        Edit
        </button>

        <button onclick="getMatchScore(${x.id})" class="btn btn-sm btn-warning mt-2">
        AI Match Score
        </button>
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
  xhr.send(); // send an HTTP request to the backend server (FASTAPI) at the URL specified in the xhr.open() method
}

function deleteApplication(id) {
  const xhr = new XMLHttpRequest();
  xhr.onload = () => { // if the request from the backend is to delete all apps, get all apps and delete type using a 'DELETE' cmd with xhr.open
    getAllApplications();
  }

  xhr.open('DELETE', `http://127.0.0.1:8000/applications/${id}`, true);
  xhr.send(); // delete the appropriate application from the backend
}

// NEW FEATURE: edit an existing job application
function editApplication(id) {

  // find current application info from DOM
  const appDiv = document.getElementById(`app-${id}`);

  const company = prompt("Enter new company name:"); // these are obtained at frontend
  const role = prompt("Enter new role:");
  const status = prompt("Enter new status (applied/interview/rejected/offer):");
  const priority = prompt("Enter new priority (high/medium/low):");
  const recruitmentinfo = prompt("Enter new recruitment info:");
  const jobpostinglink = prompt("Enter new job posting link:");

  const xhr = new XMLHttpRequest();

  xhr.onload = () => {
    getAllApplications(); // refresh list after update
  };

  xhr.open("PUT", `http://127.0.0.1:8000/applications/${id}`, true); // update all parameters
  xhr.setRequestHeader("Content-Type", "application/json");

  xhr.send(JSON.stringify({ // send all these values to backend
    company,
    role,
    status,
    priority,
    recruitmentinfo,
    jobpostinglink
  }));
}

(() => {
  getAllApplications(); // use IIFE -> get all apps after editing an application
})();

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
    const app = JSON.parse(xhr.response);

    if (resumeFile) {
      uploadResume(app.id, resumeFile);  // send resume (to backend) using xhr
    }

    getAllApplications(); // refresh application list
  };

  xhr.open("POST", "http://127.0.0.1:8000/applications/", true);
  xhr.setRequestHeader("Content-Type", "application/json");
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

  xhr.open("POST", `/applications/${appId}/resume`, true);
  xhr.send(formData); // send resume to backend for application at appId to backend
}


function getMatchScore(appId) { // get scores from backend and send to website

  const xhr = new XMLHttpRequest();

  xhr.onload = () => {
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

  xhr.open("GET", `/applications/${appId}/match`, true);
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


function register() {
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
    // ✅ STORE LOGIN STATE
    localStorage.setItem("loggedIn", "true");
    localStorage.setItem("userEmail", email);

    alert("Login successful");

    window.location.href = "/static/index.html";// switch view instead of redirect

  })
  .catch(err => alert(err.message));
}

function logout() {
  localStorage.removeItem("loggedIn");
  localStorage.removeItem("userEmail");


  alert("Logged out");

  window.location.href = "/";

}

function goToBackground() {
  window.location.href = "/static/background.html";
}

function goToApp() {
  window.location.href = "/static/index.html";
}