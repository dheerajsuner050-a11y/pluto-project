// profile.js
// Powers profile.html: loads the user's profile via GET /api/users/profile
// and saves changes via PUT /api/users/profile

const API_BASE_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", function () {
  loadProfile();

  const profileForm = document.getElementById("profileForm");
  profileForm.addEventListener("submit", saveProfile);
});

async function loadProfile() {
  const loadingEl = document.getElementById("loadingMessage");
  const formEl = document.getElementById("profileForm");

  try {
    const response = await fetch(`${API_BASE_URL}/api/users/profile`, {
      headers: {
        Authorization: "Bearer " + (localStorage.getItem("authToken") || ""),
      },
    });

    const data = await response.json();

    if (!response.ok) {
      loadingEl.textContent = data.message || "Could not load your profile.";
      return;
    }

    // Fill the form with existing data
    document.getElementById("name").value = data.name || "";
    document.getElementById("email").value = data.email || "";
    document.getElementById("phone").value = data.phone || "";
    document.getElementById("location").value = data.location || "";
    document.getElementById("education").value = data.education || "";
    document.getElementById("experience").value = data.experience || "";
    document.getElementById("skills").value = (data.skills || []).join(", ");

    // Show initial letter in the avatar circle
    const initial = (data.name || "?").trim().charAt(0).toUpperCase();
    document.getElementById("profileInitial").textContent = initial || "?";

    loadingEl.style.display = "none";
    formEl.style.display = "block";

  } catch (error) {
    console.error("Profile load error:", error);
    loadingEl.textContent = "Could not connect to the server. Please try again.";
  }
}

async function saveProfile(e) {
  e.preventDefault();

  const saveBtn = document.getElementById("saveProfileBtn");
  const messageEl = document.getElementById("profileMessage");

  const skillsArray = document
    .getElementById("skills")
    .value.split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  const profileData = {
    name: document.getElementById("name").value.trim(),
    email: document.getElementById("email").value.trim(),
    phone: document.getElementById("phone").value.trim(),
    location: document.getElementById("location").value.trim(),
    education: document.getElementById("education").value.trim(),
    experience: document.getElementById("experience").value.trim(),
    skills: skillsArray,
  };

  saveBtn.disabled = true;
  saveBtn.textContent = "Saving...";
  setMessage(messageEl, "", "");

  try {
    const response = await fetch(`${API_BASE_URL}/api/users/profile`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + (localStorage.getItem("authToken") || ""),
      },
      body: JSON.stringify(profileData),
    });

    const data = await response.json();

    if (!response.ok) {
      setMessage(messageEl, data.message || "Could not save your profile.", "error");
      return;
    }

    setMessage(messageEl, "Profile updated successfully!", "success");

  } catch (error) {
    console.error("Profile save error:", error);
    setMessage(messageEl, "Could not connect to the server. Please try again.", "error");
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save Changes";
  }
}

function setMessage(el, text, type) {
  el.textContent = text;
  el.className = "form-message" + (type ? " " + type : "");
}