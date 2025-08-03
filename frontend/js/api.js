// Backend API Communication
class ApiClient {
  static async createSigningSession(signerInfo) {
    const response = await fetch(
      `${CONFIG.backendUrl}/create-signing-session`,
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

    return await response.json();
  }

  static async getSigningStatus(sessionId) {
    const response = await fetch(
      `${CONFIG.backendUrl}/signing-status/${sessionId}`
    );

    if (!response.ok) {
      throw new Error("Failed to fetch status");
    }

    return await response.json();
  }

  static async forceCompletion(sessionId) {
    try {
      await fetch(`${CONFIG.backendUrl}/force-completion/${sessionId}`, {
        method: "POST",
      });
    } catch (err) {
      console.warn("Could not update backend status:", err);
    }
  }
}

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ApiClient };
}
