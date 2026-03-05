// ========================================
// PREMIUM UI ENHANCEMENTS - VISUAL ONLY
// Added for SaaS-level user experience
// ========================================

/**
 * Show success animation after appointment booking
 * Visual-only enhancement, no backend logic
 */
function showSuccessAnimation() {
  const animation = document.createElement('div');
  animation.className = 'success-checkmark';
  animation.innerHTML = `
    <i class="fas fa-check-circle"></i>
    <div class="success-message">Appointment Confirmed!</div>
  `;
  document.body.appendChild(animation);

  // Auto-remove after 2 seconds
  setTimeout(() => {
    animation.classList.add('fade-out');
    setTimeout(() => animation.remove(), 500);
  }, 2000);
}

/**
 * Add inline validation listeners to form fields
 * Visual feedback only, does not change validation logic
 */
function addInlineValidationListeners() {
  const fields = [
    { id: 'patientName', validator: (val) => val.trim().length > 0 },
    { id: 'patientPhone', validator: validatePhone },
    { id: 'patientEmail', validator: validateEmail }
  ];

  fields.forEach(({ id, validator }) => {
    const field = document.getElementById(id);
    if (!field) return;

    // Focus event - add focused class
    field.addEventListener('focus', () => {
      field.classList.add('field-focused');
      field.classList.remove('field-valid', 'field-invalid');
    });

    // Blur event - validate and show visual feedback
    field.addEventListener('blur', () => {
      field.classList.remove('field-focused');

      const value = field.value.trim();
      if (value) {
        if (validator(value)) {
          field.classList.add('field-valid');
          field.classList.remove('field-invalid');
        } else {
          field.classList.add('field-invalid');
          field.classList.remove('field-valid');
        }
      }
    });

    // Input event - clear invalid state while typing
    field.addEventListener('input', () => {
      if (field.classList.contains('field-invalid')) {
        field.classList.remove('field-invalid');
      }
    });
  });
}

// Initialize inline validation when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', addInlineValidationListeners);
} else {
  addInlineValidationListeners();
}
