// Dropbox Sign Event Handlers
class SigningEventHandler {
  static handleSignEvent(data) {
    console.log("Document signed:", data);
    UI.showAlert(
      "Document signed! Waiting for Dropbox confirmation...",
      ALERT_TYPES.SUCCESS
    );
    UI.updateProgress(85);
    UI.updateStatusDisplay("waiting", "Waiting for Dropbox confirmation...");

    appState.markSignEventFired();
    appState.markWaitingForConfirmation();

    // Set a timer to force completion if no other events fire
    setTimeout(() => {
      if (appState.isPolling()) {
        console.log("Forcing completion after sign event");
        SigningEventHandler.completeSigningProcess();
      }
    }, 3000);
  }

  static handleCancelEvent(data) {
    console.log("Signing cancelled:", data);
    UI.showAlert("Signing was cancelled", ALERT_TYPES.INFO);

    if (appState.hellosignClient) {
      appState.hellosignClient.close();
    }

    UI.showRetryButton();
    StatusPoller.stop();
  }

  static handleErrorEvent(data) {
    console.error("Signing error:", data);
    UI.showAlert("An error occurred during signing", ALERT_TYPES.ERROR);
    UI.showRetryButton();
    StatusPoller.stop();
  }

  static handleCloseEvent(data) {
    console.log("Signing interface closed:", data);

    // Only complete if we're in waiting state
    if (appState.waitingForConfirmation) {
      SigningEventHandler.completeSigningProcess();
    } else {
      // Treat as cancellation if not in waiting state
      UI.showAlert("Signing was cancelled", ALERT_TYPES.INFO);
      UI.showRetryButton();
      StatusPoller.stop();
    }
  }

  static handleMessageEvent(data) {
    console.log("Message from signing interface:", data);
  }

  static handleFinishEvent(data) {
    console.log("Signing process finished:", data);

    // Ensure we show waiting state even if this fires before sign event
    if (!appState.signEventFired) {
      UI.updateStatusDisplay("waiting", "Waiting for Dropbox confirmation...");
      appState.markWaitingForConfirmation();
    }

    SigningEventHandler.completeSigningProcess();
  }

  static completeSigningProcess() {
    appState.markManuallyCompleted();
    StatusPoller.stop();
    UI.updateProgress(100);
    UI.updateStatusDisplay("completed", "Document signed successfully!");
    UI.showCompletionStatus();

    // Force update backend session to completed
    if (appState.sessionId) {
      ApiClient.forceCompletion(appState.sessionId);
    }

    if (appState.hellosignClient) {
      appState.hellosignClient.close();
    }
  }
}

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { SigningEventHandler };
}
