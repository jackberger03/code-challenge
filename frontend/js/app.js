// Main Application Logic
class DocumentSigningApp {
  static async handleFormSubmit(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const signerInfo = Validator.extractSignerInfo(formData);

    if (!Validator.validateSignerInfo(signerInfo)) return;

    UI.setFormEnabled(false);
    UI.showAlert("Creating signing session...", ALERT_TYPES.INFO);

    try {
      const sessionData = await ApiClient.createSigningSession(signerInfo);
      appState.setSession(sessionData);
      CONFIG.clientId = sessionData.client_id;

      UI.showAlert(
        "Signing session created successfully!",
        ALERT_TYPES.SUCCESS
      );
      await DocumentSigningApp.initializeEmbeddedSigning();
    } catch (error) {
      console.error("Error creating signing session:", error);
      UI.showAlert(`Error: ${error.message}`, ALERT_TYPES.ERROR);
      UI.setFormEnabled(true);
    }
  }

  static async initializeEmbeddedSigning() {
    try {
      UI.showSigningContainer();

      if (!appState.hellosignClient) {
        appState.setSigningClient(
          new window.HelloSign({
            clientId: CONFIG.clientId,
          })
        );
      }

      appState.hellosignClient.open(appState.signingUrl, {
        testMode: true,
        skipDomainVerification: true,
        container: document.getElementById("signingContainer"),
        uxVersion: 2,
        events: {
          sign: SigningEventHandler.handleSignEvent,
          cancel: SigningEventHandler.handleCancelEvent,
          error: SigningEventHandler.handleErrorEvent,
          close: SigningEventHandler.handleCloseEvent,
          message: SigningEventHandler.handleMessageEvent,
          finish: SigningEventHandler.handleFinishEvent,
        },
      });

      StatusPoller.start();

      // Backup completion mechanism - force completion after 30 seconds of no events
      setTimeout(() => {
        if (appState.isPolling()) {
          console.log("Backup completion triggered - assuming signing is done");
          SigningEventHandler.completeSigningProcess();
        }
      }, 30000);
    } catch (error) {
      console.error("Error initializing embedded signing:", error);
      UI.showAlert("Failed to initialize signing interface", ALERT_TYPES.ERROR);
      UI.showRetryButton();
    }
  }

  static initialize() {
    console.log("Document Signing Portal initialized");

    // Setup phone number formatting
    UI.setupPhoneFormatting();

    // Setup form submission handler
    const form = document.getElementById("signingForm");
    form.addEventListener("submit", DocumentSigningApp.handleFormSubmit);

    // Setup cleanup on page unload
    window.addEventListener("beforeunload", function () {
      StatusPoller.stop();
      if (appState.hellosignClient) {
        appState.hellosignClient.close();
      }
    });
  }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", DocumentSigningApp.initialize);

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { DocumentSigningApp };
}
