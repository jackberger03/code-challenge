// Application State Management
class AppState {
  constructor() {
    this.reset();
  }

  reset() {
    this.sessionId = null;
    this.envelopeId = null;
    this.signingUrl = null;
    this.pollCount = 0;
    this.statusPoller = null;
    this.hellosignClient = null;
    this.manuallyCompleted = false;
    this.signEventFired = false;
    this.waitingForConfirmation = false;
  }

  setSession(sessionData) {
    this.sessionId = sessionData.session_id;
    this.envelopeId = sessionData.envelope_id;
    this.signingUrl = sessionData.signing_url;
  }

  setSigningClient(client) {
    this.hellosignClient = client;
  }

  markSignEventFired() {
    this.signEventFired = true;
  }

  markWaitingForConfirmation() {
    this.waitingForConfirmation = true;
  }

  markManuallyCompleted() {
    this.manuallyCompleted = true;
  }

  isPolling() {
    return this.statusPoller !== null;
  }

  incrementPollCount() {
    this.pollCount++;
    return this.pollCount;
  }
}

// Global state instance
const appState = new AppState();

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { AppState, appState };
}
