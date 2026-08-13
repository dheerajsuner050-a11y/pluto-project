// dashboard.js
// Powers dashboard.html.
// Uses PLACEHOLDER data for now — no backend call yet (that comes later
// when we build the backend and wire this up to a real API).

document.addEventListener("DOMContentLoaded", function () {
  loadWelcomeMessage();
  loadPlaceholderStats();
});

// Personalizes the greeting using the name saved during login (if present)
function loadWelcomeMessage() {
  const welcomeEl = document.getElementById("welcomeText");
  const userName = localStorage.getItem("userName");

  welcomeEl.textContent = userName ? `Welcome back, ${userName}!` : "Welcome back!";
}

// TODO (later step): replace this with a real fetch() call to the backend,
// e.g. GET /api/dashboard/summary
function loadPlaceholderStats() {
  const placeholderData = {
    atsScore: 78,
    skillsCount: 12,
    missingKeywords: 4,
    recommendedJobs: 6,
    resumeFileName: "john_doe_resume.pdf",
    resumeUploadDate: "Uploaded on Aug 5, 2026",
    resumeUploaded: true,
  };

  document.getElementById("atsScoreStat").textContent = placeholderData.atsScore + "%";
  document.getElementById("skillsCountStat").textContent = placeholderData.skillsCount;
  document.getElementById("missingKeywordsStat").textContent = placeholderData.missingKeywords;
  document.getElementById("recommendedJobsStat").textContent = placeholderData.recommendedJobs;

  document.getElementById("resumeFileName").textContent = placeholderData.resumeUploaded
    ? placeholderData.resumeFileName
    : "No resume uploaded yet";

  document.getElementById("resumeUploadDate").textContent = placeholderData.resumeUploaded
    ? placeholderData.resumeUploadDate
    : "—";

  const statusPill = document.getElementById("resumeStatusPill");
  if (placeholderData.resumeUploaded) {
    statusPill.textContent = "Uploaded";
    statusPill.className = "status-pill uploaded";
  } else {
    statusPill.textContent = "Not Uploaded";
    statusPill.className = "status-pill missing";
  }
}