// UI Utility Functions
class UI {
  static showAlert(message, type = ALERT_TYPES.INFO) {
    const alertContainer = document.getElementById("alertContainer");
    const alert = document.createElement("div");
    alert.className = `alert alert-${type} active`;
    alert.textContent = message;
    alertContainer.innerHTML = "";
    alertContainer.appendChild(alert);

    if (type === ALERT_TYPES.SUCCESS) {
      setTimeout(() => {
        alert.classList.remove("active");
      }, 5000);
    }
  }

  static updateStatusDisplay(status, message) {
    const statusContent = document.getElementById("statusContent");
    statusContent.innerHTML = `
      <div class="status-icon">${STATUS_ICONS[status] || "📄"}</div>
      <div class="status-message">${message}</div>
    `;
  }

  static updateProgress(percentage) {
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

  static showCompletionStatus() {
    const statusContent = document.getElementById("statusContent");

    // Add Done button to reset back to form
    const doneBtn = document.createElement("button");
    doneBtn.className = "btn btn-success";
    doneBtn.textContent = "Done";
    doneBtn.onclick = () => this.resetForm();
    statusContent.appendChild(doneBtn);
  }

  static showRetryButton() {
    const statusContent = document.getElementById("statusContent");
    const retryBtn = document.createElement("button");
    retryBtn.className = "btn btn-secondary";
    retryBtn.textContent = "🔄 Try Again";
    retryBtn.onclick = () => this.resetForm();
    statusContent.appendChild(retryBtn);
  }

  static setFormEnabled(enabled) {
    const form = document.getElementById("signingForm");
    const inputs = form.querySelectorAll("input, button");
    inputs.forEach((input) => {
      input.disabled = !enabled;
    });
  }

  static resetForm() {
    appState.reset();

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
    UI.updateProgress(0);
    UI.setFormEnabled(true);
  }

  static showSigningContainer() {
    document.getElementById("signerForm").style.display = "none";
    document.getElementById("signingContainer").classList.add("active");
  }

  static showStatusContainer() {
    document.getElementById("statusContainer").classList.add("active");
  }

  static setupPhoneFormatting() {
    const phoneInput = document.getElementById("phone");
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
}

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { UI };
}
