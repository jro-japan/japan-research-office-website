(() => {
  "use strict";

  const getLabel = (field) => {
    const label = field.id ? document.querySelector(`label[for="${CSS.escape(field.id)}"]`) : null;
    return (label?.textContent || field.getAttribute("aria-label") || field.name || "this field")
      .replace(/\s+/g, " ").replace(/[:*]+$/, "").trim();
  };

  const setEnglishMessage = (field) => {
    field.setCustomValidity("");

    if (field.validity.valueMissing) {
      if (field.type === "checkbox") {
        field.setCustomValidity(
          field.name === "privacy-consent"
            ? "Please agree to the Privacy Policy before continuing."
            : "Please select this checkbox before continuing."
        );
      } else if (field.tagName === "SELECT") {
        field.setCustomValidity("Please select an option.");
      } else {
        field.setCustomValidity(`Please enter ${getLabel(field).toLowerCase()}.`);
      }
    } else if (field.validity.typeMismatch) {
      field.setCustomValidity("Please enter a valid email address.");
    } else if (field.validity.tooShort) {
      field.setCustomValidity(`Please enter at least ${field.minLength} characters.`);
    } else if (field.validity.tooLong) {
      field.setCustomValidity(`Please enter no more than ${field.maxLength} characters.`);
    } else if (field.validity.patternMismatch) {
      field.setCustomValidity("Please enter the information in the requested format.");
    }

    if (field.validationMessage) field.setAttribute("aria-invalid", "true");
    else field.removeAttribute("aria-invalid");
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form").forEach((form) => {
      form.noValidate = true;
      const fields = [...form.querySelectorAll("input, select, textarea")]
        .filter((f) => !f.disabled && f.type !== "hidden" && f.name !== "bot-field");

      fields.forEach((field) => {
        ["input", "change"].forEach((eventName) => {
          field.addEventListener(eventName, () => {
            field.setCustomValidity("");
            field.removeAttribute("aria-invalid");
          });
        });
      });

      form.addEventListener("submit", (event) => {
        let firstInvalid = null;
        fields.forEach((field) => {
          setEnglishMessage(field);
          if (!field.checkValidity() && !firstInvalid) firstInvalid = field;
        });

        if (firstInvalid) {
          event.preventDefault();
          firstInvalid.focus();
          firstInvalid.reportValidity();
        }
      });
    });
  });
})();