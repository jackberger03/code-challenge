// Configuration and Constants
const CONFIG = {
  backendUrl: "http://localhost:8000",
  clientId: "",
  pollInterval: 3000,
  maxPollAttempts: 100,
};

// Status types and icons
const STATUS_ICONS = {
  pending: "⏳",
  waiting: "⏳",
  completed: "✅",
  declined: "❌",
  voided: "🚫",
  error: "⚠️",
};

// Alert types
const ALERT_TYPES = {
  INFO: "info",
  SUCCESS: "success",
  ERROR: "error",
  WARNING: "warning",
};

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { CONFIG, STATUS_ICONS, ALERT_TYPES };
}
