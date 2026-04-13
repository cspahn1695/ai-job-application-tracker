const email = localStorage.getItem("userEmail");

function loadBackground() {
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

window.onload = loadBackground;