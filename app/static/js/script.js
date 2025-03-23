/**
 * Main JavaScript file for the Medication Tracker application.
 */

document.addEventListener('DOMContentLoaded', function () {
  // Enable all tooltips
  var tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  var tooltipList = tooltipTriggerList.map(function (
    tooltipTriggerEl
  ) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Attach listeners for inventory adjustment buttons
  setupInventoryAdjustment();

  // Setup package calculation
  setupPackageCalculation();

  // Setup order item selection
  setupOrderItemSelection();

  // Setup visit date validation
  setupDateValidation();

  // Setup print button functionality
  setupPrintButton();
});

/**
 * Setup listeners for inventory adjustment buttons.
 */
function setupInventoryAdjustment() {
  // Quick adjustment buttons
  const quickAdjustBtns = document.querySelectorAll(
    '.quick-adjust-btn'
  );

  quickAdjustBtns.forEach((btn) => {
    btn.addEventListener('click', function () {
      const amount = parseInt(this.dataset.amount);
      const inputEl = document.getElementById('adjustment');

      if (inputEl) {
        let currentVal = parseInt(inputEl.value) || 0;
        inputEl.value = currentVal + amount;
      }
    });
  });

  // Plus/minus buttons for inventory adjustment
  const minusBtn = document.getElementById('btn-minus');
  const plusBtn = document.getElementById('btn-plus');
  const adjustmentInput = document.getElementById('adjustment');

  if (minusBtn && plusBtn && adjustmentInput) {
    minusBtn.addEventListener('click', function () {
      let value = parseInt(adjustmentInput.value) || 0;
      adjustmentInput.value = Math.max(-1000, value - 1); // Limit to reasonable values
    });

    plusBtn.addEventListener('click', function () {
      let value = parseInt(adjustmentInput.value) || 0;
      adjustmentInput.value = Math.min(1000, value + 1); // Limit to reasonable values
    });
  }
}

/**
 * Setup calculation of packages based on total units needed.
 */
function setupPackageCalculation() {
  const calculateButtons = document.querySelectorAll(
    '.calculate-packages-btn'
  );

  calculateButtons.forEach((btn) => {
    btn.addEventListener('click', function () {
      const medicationId = this.dataset.medicationId;
      const unitsInput = document.getElementById(
        `quantity_${medicationId}`
      );

      if (!unitsInput || !unitsInput.value) {
        alert('Please enter a quantity needed first.');
        return;
      }

      const unitsNeeded = parseInt(unitsInput.value);

      // Make AJAX request to calculate packages
      fetch(`/medications/${medicationId}/calculate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `units=${unitsNeeded}`,
      })
        .then((response) => response.json())
        .then((data) => {
          // Update the package inputs
          if (data.packages) {
            const n1Input = document.getElementById(
              `packages_n1_${medicationId}`
            );
            const n2Input = document.getElementById(
              `packages_n2_${medicationId}`
            );
            const n3Input = document.getElementById(
              `packages_n3_${medicationId}`
            );

            if (n1Input) n1Input.value = data.packages.N1 || 0;
            if (n2Input) n2Input.value = data.packages.N2 || 0;
            if (n3Input) n3Input.value = data.packages.N3 || 0;
          }
        })
        .catch((error) => {
          console.error('Error calculating packages:', error);
          alert('Error calculating packages. Please try again.');
        });
    });
  });
}

/**
 * Setup checkboxes for selecting medications in order creation.
 */
function setupOrderItemSelection() {
  const medicationCheckboxes = document.querySelectorAll(
    '.medication-checkbox'
  );

  medicationCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', function () {
      const medicationId = this.dataset.medicationId;
      const detailsSection = document.getElementById(
        `medication_details_${medicationId}`
      );

      if (detailsSection) {
        if (this.checked) {
          detailsSection.classList.remove('d-none');
        } else {
          detailsSection.classList.add('d-none');
        }
      }
    });
  });
}

/**
 * Setup validation for visit date inputs.
 */
function setupDateValidation() {
  const visitDateInput = document.getElementById('visit_date');

  if (visitDateInput) {
    visitDateInput.addEventListener('change', function () {
      const selectedDate = new Date(this.value);
      const today = new Date();

      // Clear out time component for comparison
      today.setHours(0, 0, 0, 0);

      if (selectedDate < today) {
        alert(
          'Warning: You have selected a date in the past. Please ensure this is correct.'
        );
      }
    });
  }
}

/**
 * Setup print button functionality.
 */
function setupPrintButton() {
  const printBtn = document.getElementById('print-order-btn');

  if (printBtn) {
    printBtn.addEventListener('click', function () {
      window.print();
    });
  }
}

/**
 * Calculate the days difference between two dates.
 *
 * @param {Date} date1 - First date
 * @param {Date} date2 - Second date
 * @return {number} - Number of days between the dates
 */
function daysBetween(date1, date2) {
  // Convert both dates to milliseconds
  const date1_ms = date1.getTime();
  const date2_ms = date2.getTime();

  // Calculate the difference in milliseconds
  let difference_ms = Math.abs(date1_ms - date2_ms);

  // Convert to days and return
  return Math.floor(difference_ms / (1000 * 60 * 60 * 24));
}

/**
 * Format a date as YYYY-MM-DD.
 *
 * @param {Date} date - The date to format
 * @return {string} - Formatted date string
 */
function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');

  return `${year}-${month}-${day}`;
}
