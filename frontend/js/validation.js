// Form Validation Logic
class Validator {
  static validateSignerInfo(signerInfo) {
    if (signerInfo.name.length < 2) {
      UI.showAlert(
        "Name must be at least 2 characters long",
        ALERT_TYPES.ERROR
      );
      return false;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(signerInfo.email)) {
      UI.showAlert("Please enter a valid email address", ALERT_TYPES.ERROR);
      return false;
    }

    if (signerInfo.phone) {
      const phoneDigits = signerInfo.phone.replace(/\D/g, "");
      if (phoneDigits.length < 10) {
        UI.showAlert(
          "Phone number must be at least 10 digits",
          ALERT_TYPES.ERROR
        );
        return false;
      }
    }

    return true;
  }

  static extractSignerInfo(formData) {
    return {
      name: formData.get("name").trim(),
      email: formData.get("email").trim(),
      phone: formData.get("phone").trim() || null,
      role_name: "Hiring Manager",
    };
  }
}

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { Validator };
}
