// auth.js
// Handles both login.html and register.html forms.
// Connects to a FastAPI backend using fetch() — no backend code here,
// this only calls the endpoints and handles the response.

// Change this if your backend runs on a different address
const API_BASE_URL = "https://pluto-project-production.up.railway.app";

document.addEventListener("DOMContentLoaded", function () {
  setupLoginForm();
  setupRegisterForm();
});

/* =========================================
   LOGIN
   ========================================= */
function setupLoginForm() {
  const loginForm = document.getElementById("loginForm");
  if (!loginForm) return; // not on login.html, skip

  const loginBtn = document.getElementById("loginBtn");
  const messageEl = document.getElementById("loginMessage");

  loginForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    setMessage(messageEl, "", "");
    setLoading(loginBtn, true, "Log In");

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setMessage(messageEl, data.message || "Invalid email or password.", "error");
        return;
      }

      // Store the auth token for this prototype (used by other pages later)
      localStorage.setItem("authToken", data.token);
      localStorage.setItem("userName", data.name || "");

      setMessage(messageEl, "Login successful! Redirecting...", "success");

      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 1000);

    } catch (error) {
      console.error("Login error:", error);
      setMessage(messageEl, "Could not connect to the server. Please try again.", "error");
    } finally {
      setLoading(loginBtn, false, "Log In");
    }
  });
}

/* =========================================
   REGISTER
   ========================================= */
function setupRegisterForm() {
  const registerForm = document.getElementById("registerForm");
  if (!registerForm) return; // not on register.html, skip

  const registerBtn = document.getElementById("registerBtn");
  const messageEl = document.getElementById("registerMessage");

  registerForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const fullName = document.getElementById("fullName").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    setMessage(messageEl, "", "");

    // Simple client-side check before calling the backend
    if (password !== confirmPassword) {
      setMessage(messageEl, "Passwords do not match.", "error");
      return;
    }

    setLoading(registerBtn, true, "Create Account");

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fullName, email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setMessage(messageEl, data.message || "Registration failed. Please try again.", "error");
        return;
      }

      setMessage(messageEl, "Account created! Redirecting to login...", "success");

      setTimeout(() => {
        window.location.href = "login.html";
      }, 1200);

    } catch (error) {
      console.error("Register error:", error);
      setMessage(messageEl, "Could not connect to the server. Please try again.", "error");
    } finally {
      setLoading(registerBtn, false, "Create Account");
    }
  });
}

/* =========================================
   SHARED HELPERS
   ========================================= */
function setMessage(el, text, type) {
  if (!el) return;
  el.textContent = text;
  el.className = "form-message" + (type ? " " + type : "");
}

function setLoading(button, isLoading, normalText) {
  if (!button) return;
  button.disabled = isLoading;
  button.textContent = isLoading ? "Please wait..." : normalText;
}