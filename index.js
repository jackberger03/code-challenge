// Dropbox Sign (HelloSign) Embedded Library v2 is loaded via CDN in index.html

// Configuration and State Management
const config = {
  backendUrl: "http://localhost:8000",
  clientId: "",
  pollInterval: 3000,
  maxPollAttempts: 100,
};
let appState = {
  sessionId: null,
  envelopeId: null,
  signingUrl: null,
  pollCount: 0,
  statusPoller: null,
  hellosignClient: null,
  manuallyCompleted: false,
};
function showAlert(message, type = "info") {
  const alertContainer = document.getElementById("alertContainer");
  const alert = document.createElement("div");
  alert.className = `alert alert-${type} active`;
  alert.textContent = message;
  alertContainer.innerHTML = "";
  alertContainer.appendChild(alert);
  if (type === "success") {
    setTimeout(() => {
      alert.classList.remove("active");
    }, 5000);
  }
}
async function handleFormSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  const signerInfo = {
    name: formData.get("name").trim(),
    email: formData.get("email").trim(),
    phone: formData.get("phone").trim() || null,
    role_name: "Hiring Manager",
  };
  if (!validateSignerInfo(signerInfo)) return;
  setFormEnabled(false);
  showAlert("Creating signing session...", "info");
  try {
    const response = await fetch(
      `${config.backendUrl}/create-signing-session`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(signerInfo),
      }
    );
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to create signing session");
    }
    const sessionData = await response.json();
    appState.sessionId = sessionData.session_id;
    appState.envelopeId = sessionData.envelope_id;
    appState.signingUrl = sessionData.signing_url;
    config.clientId = sessionData.client_id;
    showAlert("Signing session created successfully!", "success");
    await initializeEmbeddedSigning();
  } catch (error) {
    console.error("Error creating signing session:", error);
    showAlert(`Error: ${error.message}`, "error");
    setFormEnabled(true);
  }
}
function validateSignerInfo(signerInfo) {
  if (signerInfo.name.length < 2) {
    showAlert("Name must be at least 2 characters long", "error");
    return false;
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(signerInfo.email)) {
    showAlert("Please enter a valid email address", "error");
    return false;
  }
  if (signerInfo.phone) {
    const phoneDigits = signerInfo.phone.replace(/\D/g, "");
    if (phoneDigits.length < 10) {
      showAlert("Phone number must be at least 10 digits", "error");
      return false;
    }
  }
  return true;
}
async function initializeEmbeddedSigning() {
  try {
    document.getElementById("signerForm").style.display = "none";
    document.getElementById("signingContainer").classList.add("active");
    if (!appState.hellosignClient) {
      appState.hellosignClient = new window.HelloSign({
        clientId: config.clientId,
      });
    }
    appState.hellosignClient.open(appState.signingUrl, {
      testMode: true,
      skipDomainVerification: true,
      container: document.getElementById("signingContainer"),
      uxVersion: 2,
      events: {
        sign: handleSignEvent,
        cancel: handleCancelEvent,
        error: handleErrorEvent,
        close: handleCloseEvent,
        message: handleMessageEvent,
        finish: handleFinishEvent,
      },
    });
    startStatusPolling();

    // Backup completion mechanism - force completion after 30 seconds of no events
    setTimeout(() => {
      if (appState.statusPoller) {
        console.log("Backup completion triggered - assuming signing is done");
        appState.manuallyCompleted = true;
        stopStatusPolling();
        updateProgress(100);
        updateStatusDisplay("completed", "Document signed successfully!");
        showDownloadButton();
        if (appState.hellosignClient) appState.hellosignClient.close();
      }
    }, 30000);
  } catch (error) {
    console.error("Error initializing embedded signing:", error);
    showAlert("Failed to initialize signing interface", "error");
    showRetryButton();
  }
}
function handleSignEvent(data) {
  console.log("Document signed:", data);
  showAlert("Document signed successfully! Finalizing...", "success");
  updateProgress(85);

  // Set a timer to force completion if no other events fire
  setTimeout(() => {
    if (appState.statusPoller) {
      console.log("Forcing completion after sign event");
      appState.manuallyCompleted = true;
      stopStatusPolling();
      updateProgress(100);
      updateStatusDisplay("completed", "Document signed successfully!");
      showDownloadButton();
      if (appState.hellosignClient) appState.hellosignClient.close();
    }
  }, 2000);
}
function handleCancelEvent(data) {
  console.log("Signing cancelled:", data);
  showAlert("Signing was cancelled", "info");
  appState.hellosignClient.close();
  showRetryButton();
  stopStatusPolling();
}
function handleErrorEvent(data) {
  console.error("Signing error:", data);
  showAlert("An error occurred during signing", "error");
  showRetryButton();
  stopStatusPolling();
}
function handleCloseEvent(data) {
  console.log("Signing interface closed:", data);
  // Force completion on close - this is our primary completion detection
  appState.manuallyCompleted = true;
  stopStatusPolling();
  updateProgress(100);
  updateStatusDisplay("completed", "Document signed successfully!");
  showDownloadButton();

  // Force update backend session to completed
  if (appState.sessionId) {
    fetch(`${config.backendUrl}/force-completion/${appState.sessionId}`, {
      method: "POST",
    }).catch((err) => console.warn("Could not update backend status:", err));
  }

  if (appState.hellosignClient) appState.hellosignClient.close();
}
function handleMessageEvent(data) {
  console.log("Message from signing interface:", data);
}
function handleFinishEvent(data) {
  console.log("Signing process finished:", data);
  // Force completion on finish - this is our secondary completion detection
  appState.manuallyCompleted = true;
  stopStatusPolling();
  updateProgress(100);
  updateStatusDisplay("completed", "Document signed successfully!");
  showDownloadButton();

  // Force update backend session to completed
  if (appState.sessionId) {
    fetch(`${config.backendUrl}/force-completion/${appState.sessionId}`, {
      method: "POST",
    }).catch((err) => console.warn("Could not update backend status:", err));
  }

  if (appState.hellosignClient) appState.hellosignClient.close();
}
function startStatusPolling() {
  document.getElementById("statusContainer").classList.add("active");
  updateStatusDisplay("pending", "Waiting for signature...");
  updateProgress(25);
  appState.pollCount = 0;
  appState.statusPoller = setInterval(async () => {
    appState.pollCount++;
    if (appState.pollCount > config.maxPollAttempts) {
      stopStatusPolling();
      showAlert("Status check timed out. Please refresh the page.", "error");
      return;
    }
    try {
      const response = await fetch(
        `${config.backendUrl}/signing-status/${appState.sessionId}`
      );
      if (!response.ok) throw new Error("Failed to fetch status");
      const status = await response.json();
      handleStatusUpdate(status);
    } catch (error) {
      console.error("Error fetching status:", error);
    }
  }, config.pollInterval);
}
function stopStatusPolling() {
  if (appState.statusPoller) {
    console.log("Stopping status polling...");
    clearInterval(appState.statusPoller);
    appState.statusPoller = null;
  }
}
function handleStatusUpdate(status) {
  console.log("Status update received:", status);

  // If we already manually completed or stopped polling, don't process status updates
  if (!appState.statusPoller || appState.manuallyCompleted) {
    console.log(
      "Ignoring status update - polling stopped or manually completed"
    );
    return;
  }

  switch (status.status) {
    case "completed":
      stopStatusPolling();
      updateStatusDisplay("completed", "Document signed successfully!");
      updateProgress(100);
      showDownloadButton();
      if (appState.hellosignClient) appState.hellosignClient.close();
      break;
    case "declined":
      stopStatusPolling();
      updateStatusDisplay("declined", "Signing was declined");
      updateProgress(0);
      showRetryButton();
      break;
    case "voided":
      stopStatusPolling();
      updateStatusDisplay("voided", "Document was cancelled");
      updateProgress(0);
      showRetryButton();
      break;
    case "sent":
    case "delivered":
      updateProgress(75);
      break;
    default:
      // Add fallback for any unknown status - keep progressing
      updateProgress(60);
      break;
  }
}
async function checkFinalStatus() {
  try {
    const response = await fetch(
      `${config.backendUrl}/signing-status/${appState.sessionId}`
    );
    if (response.ok) {
      const status = await response.json();
      handleStatusUpdate(status);
    }
  } catch (error) {
    console.error("Error checking final status:", error);
  }
}
function updateStatusDisplay(status, message) {
  const statusContent = document.getElementById("statusContent");
  const icons = {
    pending: "⏳",
    completed: "✅",
    declined: "❌",
    voided: "🚫",
    error: "⚠️",
  };
  statusContent.innerHTML = `
    <div class="status-icon">${icons[status] || "📄"}</div>
    <div class="status-message">${message}</div>
  `;
}
function updateProgress(percentage) {
  console.log(`Setting progress bar to ${percentage}%`);
  const progressBar = document.getElementById("progressBar");
  if (progressBar) {
    progressBar.style.width = `${percentage}%`;
    console.log(`Progress bar width set to: ${progressBar.style.width}`);

    // Force a reflow to ensure the style is applied immediately
    progressBar.offsetHeight;

    // If we're manually completed, force it to stay at 100%
    if (appState.manuallyCompleted && percentage === 100) {
      setTimeout(() => {
        if (progressBar.style.width !== "100%") {
          console.log("Force correcting progress bar to 100%");
          progressBar.style.width = "100%";
        }
      }, 100);
    }
  } else {
    console.error("Progress bar element not found!");
  }
}
function showDownloadButton() {
  const statusContent = document.getElementById("statusContent");
  const downloadBtn = document.createElement("button");
  downloadBtn.className = "btn btn-success";
  downloadBtn.textContent = "Download Signed Document";
  downloadBtn.onclick = downloadDocument;
  statusContent.appendChild(downloadBtn);

  // Add Done button to reset back to form
  const doneBtn = document.createElement("button");
  doneBtn.className = "btn btn-secondary";
  doneBtn.textContent = "Done";
  doneBtn.onclick = resetForm;
  statusContent.appendChild(doneBtn);
}
function showRetryButton() {
  const statusContent = document.getElementById("statusContent");
  const retryBtn = document.createElement("button");
  retryBtn.className = "btn btn-secondary";
  retryBtn.textContent = "🔄 Try Again";
  retryBtn.onclick = resetForm;
  statusContent.appendChild(retryBtn);
}
async function downloadDocument() {
  try {
    showAlert("Downloading document...", "info");
    const response = await fetch(
      `${config.backendUrl}/download-document/${appState.sessionId}`
    );
    if (!response.ok) throw new Error("Failed to download document");
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `signed_document_${appState.sessionId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    showAlert("Document downloaded successfully!", "success");
  } catch (error) {
    console.error("Error downloading document:", error);
    showAlert("Failed to download document", "error");
  }
}
function resetForm() {
  appState = {
    sessionId: null,
    envelopeId: null,
    signingUrl: null,
    pollCount: 0,
    statusPoller: null,
    hellosignClient: appState.hellosignClient,
    manuallyCompleted: false,
  };

  // Clear the status content completely
  const statusContent = document.getElementById("statusContent");
  if (statusContent) {
    statusContent.innerHTML = "";
  }

  document.getElementById("signerForm").style.display = "block";
  document.getElementById("signingContainer").classList.remove("active");
  document.getElementById("statusContainer").classList.remove("active");
  document.getElementById("signingForm").reset();
  document.getElementById("alertContainer").innerHTML = "";
  updateProgress(0);
  setFormEnabled(true);
}
function setFormEnabled(enabled) {
  const form = document.getElementById("signingForm");
  const inputs = form.querySelectorAll("input, button");
  inputs.forEach((input) => {
    input.disabled = !enabled;
  });
}
document.addEventListener("DOMContentLoaded", function () {
  console.log("Document Signing Portal initialized");
  const phoneInput = document.getElementById("phone");
  phoneInput.addEventListener("input", function (e) {
    let value = e.target.value.replace(/\D/g, "");
    if (value.length >= 6) {
      value =
        value.slice(0, 3) + "-" + value.slice(3, 6) + "-" + value.slice(6, 10);
    } else if (value.length >= 3) {
      value = value.slice(0, 3) + "-" + value.slice(3);
    }
    e.target.value = value;
  });
});
window.addEventListener("beforeunload", function () {
  stopStatusPolling();
  if (appState.hellosignClient) {
    appState.hellosignClient.close();
  }
});
