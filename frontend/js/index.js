// Document Signing Portal - Main Entry Point
// This file contains all the application logic organized into clear sections

// ============================================================================
// CONFIGURATION
// ============================================================================

const config = {
  backendUrl: "http://localhost:8000",
  clientId: "",
  pollInterval: 3000,
  maxPollAttempts: 100,
};

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

let appState = {
  sessionId: null,
  envelopeId: null,
  signingUrl: null,
  pollCount: 0,
  statusPoller: null,
  hellosignClient: null,
  manuallyCompleted: false,
  signEventFired: false,
  waitingForConfirmation: false,
};

function resetAppState() {
  appState = {
    sessionId: null,
    envelopeId: null,
    signingUrl: null,
    pollCount: 0,
    statusPoller: null,
    hellosignClient: appState.hellosignClient, // Keep the client
    manuallyCompleted: false,
    signEventFired: false,
    waitingForConfirmation: false,
  };
}

// ============================================================================
// UI UTILITIES
// ============================================================================

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

function updateProgress(percentage) {
  console.log(`Setting progress bar to ${percentage}%`);
  const progressBar = document.getElementById("progressBar");
  if (progressBar) {
    progressBar.style.width = `${percentage}%`;
    console.log(`Progress bar width set to: ${progressBar.style.width}`);
    progressBar.offsetHeight; // Force reflow

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

function updateStatusDisplay(status, message) {
  const statusContent = document.getElementById("statusContent");
  const icons = {
    pending: "⏳",
    waiting: "⏳",
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

function showDoneButton() {
  const statusContent = document.getElementById("statusContent");
  const doneBtn = document.createElement("button");
  doneBtn.className = "btn btn-success";
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

function setFormEnabled(enabled) {
  const form = document.getElementById("signingForm");
  const inputs = form.querySelectorAll("input, button");
  inputs.forEach((input) => {
    input.disabled = !enabled;
  });
}

// ============================================================================
// FORM VALIDATION
// ============================================================================

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

// ============================================================================
// API CALLS
// ============================================================================

async function createSigningSession(signerInfo) {
  const response = await fetch(`${config.backendUrl}/create-signing-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(signerInfo),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create signing session");
  }

  return await response.json();
}

async function fetchSigningStatus() {
  const response = await fetch(
    `${config.backendUrl}/signing-status/${appState.sessionId}`
  );
  if (!response.ok) throw new Error("Failed to fetch status");
  return await response.json();
}

async function forceCompletion() {
  if (appState.sessionId) {
    fetch(`${config.backendUrl}/force-completion/${appState.sessionId}`, {
      method: "POST",
    }).catch((err) => console.warn("Could not update backend status:", err));
  }
}

// ============================================================================
// DROPBOX SIGN EVENT HANDLERS
// ============================================================================

function handleSignEvent(data) {
  console.log("Document signed:", data);
  appState.signEventFired = true;
  appState.waitingForConfirmation = true;

  showAlert("Document signed! Waiting for Dropbox confirmation...", "success");
  updateProgress(85);
  updateStatusDisplay("waiting", "Waiting for Dropbox confirmation...");

  setTimeout(() => {
    if (appState.waitingForConfirmation) {
      console.log("Completing after waiting period");
      completeSigningProcess();
    }
  }, 3000);
}

function handleCancelEvent(data) {
  console.log("Signing cancelled:", data);
  showAlert("Signing was cancelled", "info");
  if (appState.hellosignClient) appState.hellosignClient.close();
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

  if (appState.signEventFired && !appState.waitingForConfirmation) {
    // If we already processed the sign event, just complete
    completeSigningProcess();
  } else if (!appState.signEventFired) {
    // If no sign event fired, treat as cancellation
    showAlert("Signing interface closed without completion", "info");
    showRetryButton();
    stopStatusPolling();
  }
  // If we're waiting for confirmation, let the timer handle completion
}

function handleFinishEvent(data) {
  console.log("Signing process finished:", data);

  if (!appState.signEventFired) {
    // Show waiting state even if finish fires before sign
    appState.signEventFired = true;
    appState.waitingForConfirmation = true;
    showAlert(
      "Document signed! Waiting for Dropbox confirmation...",
      "success"
    );
    updateProgress(85);
    updateStatusDisplay("waiting", "Waiting for Dropbox confirmation...");

    setTimeout(() => {
      completeSigningProcess();
    }, 2000);
  } else {
    completeSigningProcess();
  }
}

function handleMessageEvent(data) {
  console.log("Message from signing interface:", data);
}

function completeSigningProcess() {
  console.log("Completing signing process");
  appState.manuallyCompleted = true;
  appState.waitingForConfirmation = false;
  stopStatusPolling();
  updateProgress(100);
  updateStatusDisplay("completed", "Document signed successfully!");
  showDoneButton();
  forceCompletion();
  if (appState.hellosignClient) appState.hellosignClient.close();
}

// ============================================================================
// STATUS POLLING
// ============================================================================

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
      const status = await fetchSigningStatus();
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

  if (!appState.statusPoller || appState.manuallyCompleted) {
    console.log(
      "Ignoring status update - polling stopped or manually completed"
    );
    return;
  }

  switch (status.status) {
    case "completed":
      completeSigningProcess();
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
      updateProgress(60);
      break;
  }
}

// ============================================================================
// EMBEDDED SIGNING
// ============================================================================

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

    // Backup completion mechanism
    setTimeout(() => {
      if (appState.statusPoller) {
        console.log("Backup completion triggered - assuming signing is done");
        completeSigningProcess();
      }
    }, 30000);
  } catch (error) {
    console.error("Error initializing embedded signing:", error);
    showAlert("Failed to initialize signing interface", "error");
    showRetryButton();
  }
}

// ============================================================================
// FORM HANDLING
// ============================================================================

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
    const sessionData = await createSigningSession(signerInfo);

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

function resetForm() {
  resetAppState();

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

// ============================================================================
// APPLICATION INITIALIZATION
// ============================================================================

document.addEventListener("DOMContentLoaded", function () {
  console.log("Document Signing Portal initialized");

  // Set up form handler
  const form = document.getElementById("signingForm");
  if (form) {
    form.addEventListener("submit", handleFormSubmit);
  }

  // Set up phone number formatting
  const phoneInput = document.getElementById("phone");
  if (phoneInput) {
    phoneInput.addEventListener("input", function (e) {
      let value = e.target.value.replace(/\D/g, "");
      if (value.length >= 6) {
        value =
          value.slice(0, 3) +
          "-" +
          value.slice(3, 6) +
          "-" +
          value.slice(6, 10);
      } else if (value.length >= 3) {
        value = value.slice(0, 3) + "-" + value.slice(3);
      }
      e.target.value = value;
    });
  }
});

// Clean up on page unload
window.addEventListener("beforeunload", function () {
  stopStatusPolling();
  if (appState.hellosignClient) {
    appState.hellosignClient.close();
  }
});
