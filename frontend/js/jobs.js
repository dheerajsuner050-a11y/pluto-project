// jobs.js
// Powers jobs.html: fetches AI-recommended jobs via GET /api/jobs/recommended
// and renders them as cards. Each card links to job-details.html?id=... 
// (job-details.html itself will be built when we get to it).

const API_BASE_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", function () {
  if (document.getElementById("jobList")) {
    loadRecommendedJobs(); // we're on jobs.html
  }
  if (document.getElementById("jobDetailsCard")) {
    loadJobDetails(); // we're on job-details.html
  }
});
async function loadRecommendedJobs() {
  const loadingEl = document.getElementById("loadingMessage");
  const errorEl = document.getElementById("errorMessage");
  const jobListEl = document.getElementById("jobList");

  try {
    const response = await fetch(`${API_BASE_URL}/api/jobs/recommended`, {
      headers: {
        Authorization: "Bearer " + (localStorage.getItem("authToken") || ""),
      },
    });

    const data = await response.json();

    if (!response.ok) {
      loadingEl.style.display = "none";
      errorEl.textContent = data.message || "Could not load job recommendations.";
      return;
    }

    renderJobs(data.jobs || data); // supports either { jobs: [...] } or a plain array

    loadingEl.style.display = "none";

  } catch (error) {
    console.error("Jobs fetch error:", error);
    loadingEl.style.display = "none";
    errorEl.textContent = "Could not connect to the server. Please try again.";
  }
}

function renderJobs(jobs) {
  const jobListEl = document.getElementById("jobList");

  if (!jobs || jobs.length === 0) {
    jobListEl.innerHTML = "<p>No job recommendations yet. Try uploading a resume first.</p>";
    return;
  }

  jobs.forEach((job) => {
    const skillsHtml = (job.skills || [])
      .map((skill) => `<span class="badge badge-primary">${skill}</span>`)
      .join("");

    jobListEl.innerHTML += `
      <div class="card job-card">
        <div class="job-card-header">
          <div>
            <h3>${job.title}</h3>
            <p class="job-company">${job.company}</p>
          </div>
          <span class="match-badge">${job.matchPercent}% Match</span>
        </div>
        <p class="job-location">📍 ${job.location}</p>
        <p class="job-description">${job.description}</p>
        <div class="job-skills">${skillsHtml}</div>
        <a href="job-details.html?id=${job.id}" class="btn btn-block">View Details</a>
      </div>
    `;
  });
}