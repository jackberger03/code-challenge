// Status Polling Logic
class StatusPoller {
  static start() {
    UI.showStatusContainer();
    UI.updateStatusDisplay("pending", "Waiting for signature...");
    UI.updateProgress(25);

    appState.pollCount = 0;
    appState.statusPoller = setInterval(async () => {
      const pollCount = appState.incrementPollCount();

      if (pollCount > CONFIG.maxPollAttempts) {
        StatusPoller.stop();
        UI.showAlert(
          "Status check timed out. Please refresh the page.",
          ALERT_TYPES.ERROR
        );
        return;
      }

      try {
        const status = await ApiClient.getSigningStatus(appState.sessionId);
        StatusPoller.handleStatusUpdate(status);
      } catch (error) {
        console.error("Error fetching status:", error);
      }
    }, CONFIG.pollInterval);
  }

  static stop() {
    if (appState.statusPoller) {
      console.log("Stopping status polling...");
      clearInterval(appState.statusPoller);
      appState.statusPoller = null;
    }
  }

  static handleStatusUpdate(status) {
    console.log("Status update received:", status);

    // If we already manually completed or stopped polling, don't process status updates
    if (!appState.isPolling() || appState.manuallyCompleted) {
      console.log(
        "Ignoring status update - polling stopped or manually completed"
      );
      return;
    }

    switch (status.status) {
      case "completed":
        StatusPoller.stop();
        UI.updateStatusDisplay("completed", "Document signed successfully!");
        UI.updateProgress(100);
        UI.showCompletionStatus();
        if (appState.hellosignClient) {
          appState.hellosignClient.close();
        }
        break;

      case "declined":
        StatusPoller.stop();
        UI.updateStatusDisplay("declined", "Signing was declined");
        UI.updateProgress(0);
        UI.showRetryButton();
        break;

      case "voided":
        StatusPoller.stop();
        UI.updateStatusDisplay("voided", "Document was cancelled");
        UI.updateProgress(0);
        UI.showRetryButton();
        break;

      case "sent":
      case "delivered":
        UI.updateProgress(75);
        break;

      default:
        // Add fallback for any unknown status - keep progressing
        UI.updateProgress(60);
        break;
    }
  }

  static async checkFinalStatus() {
    try {
      const status = await ApiClient.getSigningStatus(appState.sessionId);
      StatusPoller.handleStatusUpdate(status);
    } catch (error) {
      console.error("Error checking final status:", error);
    }
  }
}

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { StatusPoller };
}
