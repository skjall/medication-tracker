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

  // Setup product selection changes
  setupProductSelection();
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
      const ingredientId = this.dataset.ingredientId;
      const unitsInput = document.getElementById(
        `quantity_${ingredientId}`
      );

      if (!unitsInput || !unitsInput.value) {
        alert('Please enter a quantity needed first.');
        return;
      }

      const unitsNeeded = parseInt(unitsInput.value);

      // Make AJAX request to calculate packages
      fetch(`/ingredients/${ingredientId}/calculate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `units=${unitsNeeded}&calculation=additional`,
      })
        .then((response) => response.json())
        .then((data) => {
          // Update the package inputs
          if (data.packages) {
            // Handle both new ProductPackage system and legacy N1/N2/N3
            Object.keys(data.packages).forEach(packageName => {
              // Try new package naming convention first
              let input = document.getElementById(
                `packages_${packageName}_${ingredientId}`
              );
              
              // Fall back to legacy naming if not found
              if (!input && packageName.startsWith('N')) {
                input = document.getElementById(
                  `packages_${packageName.toLowerCase()}_${ingredientId}`
                );
              }
              
              if (input) {
                input.value = data.packages[packageName] || 0;
              }
            });
            
            // Also clear any package inputs not in the response
            const allPackageInputs = document.querySelectorAll(
              `input[id^="packages_"][id$="_${ingredientId}"]`
            );
            allPackageInputs.forEach(input => {
              const packageNameMatch = input.id.match(/packages_(.+)_\d+/);
              if (packageNameMatch) {
                const packageName = packageNameMatch[1];
                // Check both exact match and uppercase version for legacy
                if (!data.packages[packageName] && 
                    !data.packages[packageName.toUpperCase()]) {
                  input.value = 0;
                }
              }
            });
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
 * Setup checkboxes for selecting ingredients in order creation.
 */
function setupOrderItemSelection() {
  const ingredientCheckboxes = document.querySelectorAll(
    '.ingredient-checkbox'
  );

  ingredientCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', function () {
      const ingredientId = this.dataset.ingredientId;
      const detailsSection = document.getElementById(
        `ingredient_details_${ingredientId}`
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

/**
 * Setup product selection dropdowns.
 * When a product is changed, update the package inputs and recalculate.
 */
function setupProductSelection() {
  const productSelectors = document.querySelectorAll('.product-selector');
  
  productSelectors.forEach((selector) => {
    selector.addEventListener('change', function() {
      const medicationId = this.dataset.medicationId;
      const selectedOption = this.options[this.selectedIndex];
      const packagesData = selectedOption.dataset.packages;
      
      if (packagesData) {
        try {
          const packages = JSON.parse(packagesData);
          updatePackageInputs(medicationId, packages);
          
          // Trigger recalculation if quantity is set
          const quantityInput = document.getElementById(`quantity_${medicationId}`);
          if (quantityInput && quantityInput.value) {
            // Trigger the calculate button click
            const calculateBtn = document.querySelector(`.calculate-packages-btn[data-medication-id="${medicationId}"]`);
            if (calculateBtn) {
              calculateBtn.click();
            }
          }
        } catch (e) {
          console.error('Error parsing package data:', e);
        }
      }
    });
  });
}

/**
 * Update package inputs based on selected product packages.
 */
function updatePackageInputs(medicationId, packages) {
  // First, hide all existing package inputs for this medication
  const allPackageInputs = document.querySelectorAll(`input[id^="packages_"][id$="_${medicationId}"]`);
  allPackageInputs.forEach(input => {
    input.closest('.col-md-4').style.display = 'none';
  });
  
  // Get the container for package inputs
  const detailsRow = document.getElementById(`medication_details_${medicationId}`);
  if (!detailsRow) return;
  
  const packageContainer = detailsRow.querySelector('.row > .col-md-8 > .mb-3 > .row');
  if (!packageContainer) return;
  
  // Clear and rebuild package inputs for new product
  packageContainer.innerHTML = '';
  
  packages.forEach(pkg => {
    if (pkg.quantity > 0) {
      const packageDiv = document.createElement('div');
      packageDiv.className = 'col-md-4';
      packageDiv.innerHTML = `
        <div class="input-group mb-2">
          <span class="input-group-text">${pkg.package_size}</span>
          <input type="number" class="form-control" 
                 id="packages_${pkg.package_size}_${medicationId}" 
                 name="packages_${pkg.package_size}_${medicationId}" 
                 min="0" value="0">
        </div>
        <small class="text-muted">${pkg.quantity} units each</small>
      `;
      packageContainer.appendChild(packageDiv);
    }
  });
}
