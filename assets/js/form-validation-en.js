/**
 * Japan Research Office — custom English form validation v7.1
 * Replaces browser/OS-localized validation bubbles with accessible English messages.
 */
(() => {
  "use strict";

  const FORM_SELECTOR = [
    "form[data-jro-validation]",
    "form[data-netlify='true']",
    "form[netlify]",
    "form[name='contact']",
    "form[name='general-inquiry']",
    "form[name='sample-request']"
  ].join(", ");

  const FIELD_SELECTOR = "input, select, textarea";
  const EXCLUDED_TYPES = new Set(["hidden", "submit", "button", "reset", "image"]);

  const normalize = (value) => String(value || "").trim();
  const generatedFieldKeys = new WeakMap();

  const fieldKey = (field) => {
    const explicit = normalize(field.id || field.name).replace(/[^a-zA-Z0-9_-]+/g, "-");
    if (explicit) return explicit;
    if (!generatedFieldKeys.has(field)) {
      generatedFieldKeys.set(field, `field-${Math.random().toString(36).slice(2)}`);
    }
    return generatedFieldKeys.get(field);
  };

  const fieldToken = (field) => normalize(`${field.name || ""} ${field.id || ""}`).toLowerCase();

  const readableLabel = (field) => {
    const explicit = normalize(field.dataset.validationLabel);
    if (explicit) return explicit;

    const token = fieldToken(field);
    if (token.includes("company") || token.includes("organization")) return "company name";
    if (token.includes("email")) return "work email address";
    if (token.includes("service")) return "service";
    if (token.includes("message") || token.includes("detail") || token.includes("project")) return "project details";
    if (token.includes("privacy") || token.includes("consent") || token.includes("terms")) return "Privacy Policy";
    if (token.includes("name")) return "name";

    const label = field.id
      ? document.querySelector(`label[for="${CSS.escape(field.id)}"]`)
      : null;
    const labelText = normalize(label?.textContent).replace(/\s*\*\s*$/, "");
    return labelText || "this field";
  };

  const customMessage = (field, key) => normalize(field.dataset[key]);

  const getRadioGroup = (field) => {
    if (field.type !== "radio" || !field.name || !field.form) return [field];
    return [...field.form.elements].filter((item) => item.type === "radio" && item.name === field.name);
  };

  const isEmpty = (field) => {
    if (field.type === "checkbox") return !field.checked;
    if (field.type === "radio") return !getRadioGroup(field).some((item) => item.checked);
    if (field.tagName === "SELECT" && field.multiple) {
      return field.selectedOptions.length === 0;
    }
    return normalize(field.value) === "";
  };

  const validationMessage = (field) => {
    const validity = field.validity;
    const label = readableLabel(field);
    const token = fieldToken(field);

    if (validity.valueMissing || (field.required && isEmpty(field))) {
      const override = customMessage(field, "errorRequired");
      if (override) return override;
      if (field.type === "checkbox" && /privacy|consent|terms/.test(token)) {
        return "Please accept the Privacy Policy before submitting.";
      }
      if (field.type === "checkbox") return "Please select this option.";
      if (field.type === "radio") return `Please select your ${label}.`;
      if (field.tagName === "SELECT") return `Please select a ${label}.`;
      if (label === "project details") return "Please describe your project.";
      return `Please enter your ${label}.`;
    }

    if (validity.typeMismatch) {
      return customMessage(field, "errorType") ||
        (field.type === "email"
          ? "Please enter a valid work email address."
          : `Please enter a valid ${label}.`);
    }

    if (validity.patternMismatch) {
      return customMessage(field, "errorPattern") || `Please enter a valid ${label}.`;
    }

    if (validity.tooShort) {
      return customMessage(field, "errorTooShort") ||
        `Please enter at least ${field.minLength} characters.`;
    }

    if (validity.tooLong) {
      return customMessage(field, "errorTooLong") ||
        `Please enter no more than ${field.maxLength} characters.`;
    }

    if (validity.rangeUnderflow) {
      return customMessage(field, "errorRange") || `Please enter a value of at least ${field.min}.`;
    }

    if (validity.rangeOverflow) {
      return customMessage(field, "errorRange") || `Please enter a value no greater than ${field.max}.`;
    }

    if (validity.stepMismatch || validity.badInput) {
      return customMessage(field, "errorType") || `Please enter a valid ${label}.`;
    }

    return customMessage(field, "errorInvalid") || "Please review this field.";
  };

  const errorHost = (field) =>
    field.closest(".form-field, .field, .form-group") || field.parentElement;

  const ensureErrorNode = (field) => {
    const owner = field.type === "radio" ? getRadioGroup(field)[0] : field;
    const errorId = `${fieldKey(owner)}-error`;
    let node = document.getElementById(errorId);

    if (!node) {
      node = document.createElement("p");
      node.id = errorId;
      node.className = "form-error-message";
      node.setAttribute("role", "alert");
      node.setAttribute("aria-live", "polite");
      node.hidden = true;
      errorHost(owner)?.appendChild(node);
    }

    getRadioGroup(field).forEach((item) => {
      const ids = new Set(normalize(item.getAttribute("aria-describedby")).split(/\s+/).filter(Boolean));
      ids.add(errorId);
      item.setAttribute("aria-describedby", [...ids].join(" "));
    });

    return node;
  };

  const clearError = (field) => {
    const group = getRadioGroup(field);
    group.forEach((item) => {
      item.classList.remove("has-error");
      item.removeAttribute("aria-invalid");
      item.setCustomValidity("");
    });

    const owner = group[0];
    const node = document.getElementById(`${fieldKey(owner)}-error`);
    if (node) {
      node.textContent = "";
      node.hidden = true;
    }
  };

  const validateField = (field) => {
    clearError(field);

    if (field.disabled || EXCLUDED_TYPES.has(field.type)) return true;

    const requiredMissing = field.required && isEmpty(field);
    const invalid = requiredMissing || !field.validity.valid;
    if (!invalid) return true;

    const node = ensureErrorNode(field);
    node.textContent = validationMessage(field);
    node.hidden = false;

    getRadioGroup(field).forEach((item) => {
      item.classList.add("has-error");
      item.setAttribute("aria-invalid", "true");
    });
    return false;
  };

  const initForm = (form) => {
    if (form.dataset.jroValidationReady === "true") return;
    form.dataset.jroValidationReady = "true";

    // Applied only after JavaScript has loaded. If JavaScript fails, native HTML validation remains available.
    form.noValidate = true;

    const fields = [...form.querySelectorAll(FIELD_SELECTOR)].filter((field) =>
      !field.disabled &&
      !EXCLUDED_TYPES.has(field.type) &&
      field.name !== "bot-field"
    );

    fields.forEach((field) => {
      const clearEvents = field.type === "checkbox" || field.type === "radio"
        ? ["change"]
        : ["input", "change"];

      clearEvents.forEach((eventName) => {
        field.addEventListener(eventName, () => clearError(field));
      });

      field.addEventListener("blur", () => {
        if (field.required || !isEmpty(field)) validateField(field);
      });
    });

    form.addEventListener("submit", (event) => {
      let firstInvalid = null;
      const validatedRadioNames = new Set();

      fields.forEach((field) => {
        if (field.type === "radio" && field.name) {
          if (validatedRadioNames.has(field.name)) return;
          validatedRadioNames.add(field.name);
        }

        if (!validateField(field) && !firstInvalid) firstInvalid = field;
      });

      if (!firstInvalid) return;

      event.preventDefault();
      firstInvalid.focus({ preventScroll: true });
      firstInvalid.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  };

  const init = () => document.querySelectorAll(FORM_SELECTOR).forEach(initForm);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
