// resume.js
// Powers upload-resume.html: drag & drop, file selection, validation,
// and uploading the resume to the backend via fetch().

const API_BASE_URL = "http://127.0.0.1:8000";
const MAX_FILE_SIZE_MB = 5;
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];

let selectedFile = null;

document.addEventListener("DOMContentLoaded", function () {
  const uploadBox = document.getElementById("uploadBox");
  const fileInput = document.getElementById("fileInput");
  const fileInfoCard = document.getElementById("fileInfoCard");
  const fileNameEl = document.getElementById("fileName");
  const fileSizeEl = document.getElementById("fileSize");
  const removeFileBtn = document.getElementById("removeFileBtn");
  const uploadBtn = document.getElementById("uploadBtn");
  const messageEl = document.getElementById("uploadMessage");

  uploadBox.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) handleFile(e.target.files[0]);
  });

  uploadBox.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadBox.classList.add("drag-over");
  });

  uploadBox.addEventListener("dragleave", () => {
    uploadBox.classList.remove("drag-over");
  });

  uploadBox.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadBox.classList.remove("drag-over");
    if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
  });

  removeFileBtn.addEventListener("click", () => {
    resetFileSelection();
  });

  uploadBtn.addEventListener("click", uploadResume);

  function handleFile(file) {
    setMessage("", "");

    const fileName = file.name.toLowerCase();
    const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) => fileName.endsWith(ext));

    if (!hasValidExtension) {
      setMessage("Only PDF or DOCX files are allowed.", "error");
      resetFileSelection();
      return;
    }

    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > MAX_FILE_SIZE_MB) {
      setMessage(`File is too large. Max size is ${MAX_FILE_SIZE_MB}MB.`, "error");
      resetFileSelection();
      return;
    }

    selectedFile = file;
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = fileSizeMB.toFixed(2) + " MB";
    fileInfoCard.classList.add("show");
    uploadBtn.disabled = false;
  }

  function resetFileSelection() {
    selectedFile = null;
    fileInput.value = "";
    fileInfoCard.classList.remove("show");
    uploadBtn.disabled = true;
  }

  async function uploadResume() {
    if (!selectedFile) return;

    setMessage("", "");
    setUploading(true);

    const formData = new FormData();
    formData.append("resume", selectedFile);

    try {
      const response = await fetch(`${API_BASE_URL}/api/resumes/upload`, {
        method: "POST",
        headers: {
          Authorization: "Bearer " + (localStorage.getItem("authToken") || ""),
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.message || data.detail || "Upload failed. Please try again.", "error");
        return;
      }

      if (data.resumeId) {
        localStorage.setItem("resumeId", data.resumeId);
      }

      setMessage("Resume uploaded successfully! Redirecting to your ATS report...", "success");

      setTimeout(() => {
        window.location.href = "ats-result.html";
      }, 1200);

    } catch (error) {
      console.error("Upload error:", error);
      setMessage("Could not connect to the server. Please try again.", "error");
    } finally {
      setUploading(false);
    }
  }

  function setUploading(isUploading) {
    uploadBtn.disabled = isUploading;
    document.getElementById("uploadBtnText").textContent = isUploading ? "Uploading..." : "Upload Resume";
    document.getElementById("uploadSpinner").classList.toggle("show", isUploading);
  }

  function setMessage(text, type) {
    messageEl.textContent = text;
    messageEl.className = "form-message" + (type ? " " + type : "");
  }
});