// ats.js
// Powers ats-result.html: fetches the ATS report for the uploaded resume
// via GET /api/ats/reports/{id}

const API_BASE_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", loadAtsReport);

async function loadAtsReport() {
  const loadingEl = document.getElementById("loadingMessage");
  const errorEl = document.getElementById("errorMessage");
  const reportBody = document.getElementById("reportBody");

  const resumeId = localStorage.getItem("resumeId");

  if (!resumeId) {
    loadingEl.style.display = "none";
    errorEl.textContent = "No resume found. Please upload a resume first.";
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/ats/reports/${resumeId}`, {
      headers: {
        Authorization: "Bearer " + (localStorage.getItem("authToken") || ""),
      },
    });

    const data = await response.json();

    if (!response.ok) {
      loadingEl.style.display = "none";
      errorEl.textContent = data.message || "Could not load your ATS report.";
      return;
    }

    renderReport(data);

    loadingEl.style.display = "none";
    reportBody.style.display = "block";

  } catch (error) {
    console.error("ATS report error:", error);
    loadingEl.style.display = "none";
    errorEl.textContent = "Could not connect to the server. Please try again.";
  }
}

function renderReport(data) {
  // Overall score
  document.getElementById("scoreCircle").style.setProperty("--score", data.overallScore);
  document.getElementById("overallScore").textContent = data.overallScore;

  // Breakdown bars
  const breakdownList = document.getElementById("breakdownList");
  const breakdownItems = [
    { label: "Keyword Match", value: data.keywordScore },
    { label: "Skills Match", value: data.skillsScore },
    { label: "Experience", value: data.experienceScore },
    { label: "Education", value: data.educationScore },
    { label: "Formatting", value: data.formattingScore },
  ];

  breakdownItems.forEach((item) => {
    breakdownList.innerHTML += `
      <div class="breakdown-item">
        <div class="breakdown-item-header">
          <span>${item.label}</span>
          <span>${item.value}%</span>
        </div>
        <div class="breakdown-bar-track">
          <div class="breakdown-bar-fill" style="width: ${item.value}%;"></div>
        </div>
      </div>
    `;
  });

  // Matched keywords
  const matchedEl = document.getElementById("matchedKeywords");
  (data.matchedKeywords || []).forEach((kw) => {
    matchedEl.innerHTML += `<span class="badge badge-matched">${kw}</span>`;
  });

  // Missing keywords
  const missingEl = document.getElementById("missingKeywords");
  (data.missingKeywords || []).forEach((kw) => {
    missingEl.innerHTML += `<span class="badge badge-missing">${kw}</span>`;
  });

  // Suggestions
  const suggestionsEl = document.getElementById("suggestionsList");
  (data.suggestions || []).forEach((suggestion) => {
    suggestionsEl.innerHTML += `
      <li>
        <span class="suggestion-icon">💡</span>
        <span>${suggestion}</span>
      </li>
    `;
  });
}