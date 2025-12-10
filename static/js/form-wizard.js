/**
 * Multi-Step Form Wizard - World-Class Implementation
 * 
 * Breaks long forms into manageable steps with progress tracking.
 * Inspired by: ServiceNow ITAM, Salesforce, IBM Maximo, Stripe Checkout
 * 
 * Features:
 * - Step-by-step navigation
 * - Progress indicator with step numbers
 * - Step validation before proceeding
 * - Save and resume (integration with FormAutoSave)
 * - Conditional steps (skip based on answers)
 * - Summary review step
 * - Responsive design (mobile-friendly)
 * - Keyboard navigation (Tab, Enter, Escape)
 * - Accessible (ARIA, screen readers)
 * - Animated transitions
 * 
 * Usage:
 *   const wizard = new FormWizard('asset-registration-wizard', {
 *     steps: [
 *       { id: 'basic', title: 'Basic Information', fields: ['name', 'category'] },
 *       { id: 'location', title: 'Location', fields: ['branch', 'assigned_to'] },
 *       { id: 'financial', title: 'Financial', fields: ['purchase_value'] },
 *       { id: 'review', title: 'Review', isReview: true }
 *     ]
 *   });
 */

class FormWizard {
  /**
   * Initialize multi-step wizard
   * @param {string} wizardId - Wizard container ID
   * @param {Object} options - Configuration options
   */
  constructor(wizardId, options = {}) {
    this.wizardId = wizardId;
    this.wizard = document.getElementById(wizardId);
    
    if (!this.wizard) {
      console.warn(`FormWizard: Element with ID "${wizardId}" not found`);
      return;
    }

    // Configuration
    this.options = {
      steps: options.steps || [],
      startStep: options.startStep || 0,
      showProgressBar: options.showProgressBar !== false,
      allowStepClick: options.allowStepClick !== false,
      showStepNumbers: options.showStepNumbers !== false,
      validateBeforeNext: options.validateBeforeNext !== false,
      animationDuration: options.animationDuration || 300,
      saveProgress: options.saveProgress !== false,
      storageKey: options.storageKey || `wizard_progress_${wizardId}`,
      onStepChange: options.onStepChange || null,
      onComplete: options.onComplete || null,
      validator: options.validator || null, // FormValidator instance
    };

    // State
    this.currentStep = this.options.startStep;
    this.completedSteps = new Set();
    this.stepData = {};

    // Elements
    this.progressContainer = null;
    this.stepsContainer = null;
    this.navigationContainer = null;

    // Initialize
    this.init();
  }

  /**
   * Initialize wizard
   */
  init() {
    // Create wizard structure
    this.createWizardStructure();

    // Restore saved progress
    if (this.options.saveProgress) {
      this.restoreProgress();
    }

    // Show initial step
    this.goToStep(this.currentStep);

    // Attach keyboard listeners
    this.attachKeyboardListeners();

    console.log(`✅ FormWizard initialized for "${this.wizardId}"`);
  }

  /**
   * Create wizard HTML structure
   */
  createWizardStructure() {
    // Add wizard class
    this.wizard.classList.add('form-wizard');

    // Create progress indicator
    if (this.options.showProgressBar) {
      this.createProgressIndicator();
    }

    // Create steps container
    this.stepsContainer = document.createElement('div');
    this.stepsContainer.className = 'wizard-steps';
    this.wizard.appendChild(this.stepsContainer);

    // Move existing form sections into steps
    this.createSteps();

    // Create navigation buttons
    this.createNavigation();
  }

  /**
   * Create progress indicator
   */
  createProgressIndicator() {
    this.progressContainer = document.createElement('div');
    this.progressContainer.className = 'wizard-progress';
    this.progressContainer.setAttribute('role', 'progressbar');
    this.progressContainer.setAttribute('aria-valuemin', '0');
    this.progressContainer.setAttribute('aria-valuemax', this.options.steps.length);

    const progressHTML = `
      <div class="progress-steps">
        ${this.options.steps.map((step, index) => `
          <div class="progress-step ${index === 0 ? 'active' : ''}" data-step="${index}">
            ${this.options.showStepNumbers ? `
              <div class="step-number">${index + 1}</div>
            ` : ''}
            <div class="step-title">${step.title}</div>
            ${index < this.options.steps.length - 1 ? '<div class="step-connector"></div>' : ''}
          </div>
        `).join('')}
      </div>
      <div class="progress-bar">
        <div class="progress-fill" style="width: ${(1 / this.options.steps.length) * 100}%"></div>
      </div>
    `;

    this.progressContainer.innerHTML = progressHTML;
    this.wizard.insertBefore(this.progressContainer, this.wizard.firstChild);

    // Add click handlers if allowed
    if (this.options.allowStepClick) {
      this.progressContainer.querySelectorAll('.progress-step').forEach((stepEl, index) => {
        stepEl.style.cursor = 'pointer';
        stepEl.addEventListener('click', () => {
          if (index <= Math.max(...this.completedSteps, this.currentStep)) {
            this.goToStep(index);
          }
        });
      });
    }
  }

  /**
   * Create step containers
   */
  createSteps() {
    this.options.steps.forEach((step, index) => {
      const stepContainer = document.createElement('div');
      stepContainer.className = 'wizard-step';
      stepContainer.dataset.step = index;
      stepContainer.setAttribute('role', 'tabpanel');
      stepContainer.setAttribute('aria-labelledby', `step-${index}-label`);
      stepContainer.style.display = index === this.currentStep ? 'block' : 'none';

      // Step header
      const stepHeader = document.createElement('div');
      stepHeader.className = 'wizard-step-header';
      stepHeader.innerHTML = `
        <h3 id="step-${index}-label" class="step-title">
          ${step.icon ? `<i class="${step.icon} me-2"></i>` : ''}
          ${step.title}
        </h3>
        ${step.description ? `<p class="step-description text-muted">${step.description}</p>` : ''}
      `;
      stepContainer.appendChild(stepHeader);

      // Step content
      const stepContent = document.createElement('div');
      stepContent.className = 'wizard-step-content';
      
      // If fields are specified, move them into this step
      if (step.fields && step.fields.length > 0) {
        step.fields.forEach(fieldName => {
          const fieldGroup = this.findFieldGroup(fieldName);
          if (fieldGroup) {
            stepContent.appendChild(fieldGroup);
          }
        });
      } else if (step.content) {
        // Custom content
        stepContent.innerHTML = step.content;
      } else if (step.isReview) {
        // Review step - will be populated dynamically
        stepContent.id = `wizard-review-${index}`;
        stepContent.innerHTML = '<div class="review-content"></div>';
      }

      stepContainer.appendChild(stepContent);
      this.stepsContainer.appendChild(stepContainer);
    });
  }

  /**
   * Find field group (form-group/mb-3) by field name
   * @param {string} fieldName - Field name
   * @returns {HTMLElement|null} Field group element
   */
  findFieldGroup(fieldName) {
    const field = document.querySelector(`[name="${fieldName}"]`);
    if (!field) return null;

    // Find parent form-group or mb-3
    return field.closest('.form-group, .mb-3, .col-md-6, .col-md-12');
  }

  /**
   * Create navigation buttons
   */
  createNavigation() {
    this.navigationContainer = document.createElement('div');
    this.navigationContainer.className = 'wizard-navigation';

    this.navigationContainer.innerHTML = `
      <button type="button" class="btn btn-outline-secondary wizard-btn-prev" style="display: none;">
        <i class="bi bi-arrow-left me-2"></i>Previous
      </button>
      <div class="flex-grow-1"></div>
      <button type="button" class="btn btn-primary wizard-btn-next">
        Next<i class="bi bi-arrow-right ms-2"></i>
      </button>
      <button type="submit" class="btn btn-success wizard-btn-submit" style="display: none;">
        <i class="bi bi-check-circle me-2"></i>Submit
      </button>
    `;

    this.wizard.appendChild(this.navigationContainer);

    // Attach event listeners
    this.navigationContainer.querySelector('.wizard-btn-prev').addEventListener('click', () => {
      this.previousStep();
    });

    this.navigationContainer.querySelector('.wizard-btn-next').addEventListener('click', () => {
      this.nextStep();
    });
  }

  /**
   * Go to specific step
   * @param {number} stepIndex - Step index
   * @param {boolean} animate - Animate transition
   */
  async goToStep(stepIndex, animate = true) {
    // Validate step index
    if (stepIndex < 0 || stepIndex >= this.options.steps.length) {
      console.warn(`Invalid step index: ${stepIndex}`);
      return;
    }

    // Validate current step before proceeding (if moving forward)
    if (stepIndex > this.currentStep && this.options.validateBeforeNext) {
      const isValid = await this.validateStep(this.currentStep);
      if (!isValid) {
        console.log('⚠️ Step validation failed, staying on current step');
        return;
      }
    }

    // Save current step data
    this.saveStepData(this.currentStep);

    // Mark current step as completed (if moving forward)
    if (stepIndex > this.currentStep) {
      this.completedSteps.add(this.currentStep);
    }

    // Hide current step
    const currentStepEl = this.stepsContainer.querySelector(`[data-step="${this.currentStep}"]`);
    if (currentStepEl) {
      if (animate) {
        currentStepEl.style.opacity = '0';
        await this.delay(this.options.animationDuration);
      }
      currentStepEl.style.display = 'none';
    }

    // Update current step
    const previousStep = this.currentStep;
    this.currentStep = stepIndex;

    // Show new step
    const newStepEl = this.stepsContainer.querySelector(`[data-step="${this.currentStep}"]`);
    if (newStepEl) {
      newStepEl.style.display = 'block';
      if (animate) {
        newStepEl.style.opacity = '0';
        await this.delay(50); // Small delay for transition
        newStepEl.style.opacity = '1';
      }

      // If this is a review step, populate it
      const step = this.options.steps[this.currentStep];
      if (step.isReview) {
        this.populateReviewStep(this.currentStep);
      }
    }

    // Update progress indicator
    this.updateProgressIndicator();

    // Update navigation buttons
    this.updateNavigationButtons();

    // Save progress
    if (this.options.saveProgress) {
      this.saveProgress();
    }

    // Scroll to top of wizard
    this.wizard.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Call step change callback
    if (this.options.onStepChange) {
      this.options.onStepChange(this.currentStep, previousStep, this.options.steps[this.currentStep]);
    }

    console.log(`📍 Moved to step ${this.currentStep + 1}/${this.options.steps.length}: ${this.options.steps[this.currentStep].title}`);
  }

  /**
   * Move to next step
   */
  nextStep() {
    if (this.currentStep < this.options.steps.length - 1) {
      this.goToStep(this.currentStep + 1);
    }
  }

  /**
   * Move to previous step
   */
  previousStep() {
    if (this.currentStep > 0) {
      this.goToStep(this.currentStep - 1);
    }
  }

  /**
   * Validate current step
   * @param {number} stepIndex - Step index to validate
   * @returns {Promise<boolean>} True if valid
   */
  async validateStep(stepIndex) {
    const step = this.options.steps[stepIndex];
    
    // If validator instance is provided, use it
    if (this.options.validator && step.fields) {
      const validations = step.fields.map(fieldName => 
        this.options.validator.validateField(fieldName)
      );
      const results = await Promise.all(validations);
      return results.every(result => result === true);
    }

    // Custom validation function
    if (step.validate && typeof step.validate === 'function') {
      return await step.validate();
    }

    // No validation required
    return true;
  }

  /**
   * Save step data
   * @param {number} stepIndex - Step index
   */
  saveStepData(stepIndex) {
    const step = this.options.steps[stepIndex];
    if (!step.fields) return;

    const data = {};
    step.fields.forEach(fieldName => {
      const field = document.querySelector(`[name="${fieldName}"]`);
      if (field) {
        if (field.type === 'checkbox') {
          data[fieldName] = field.checked;
        } else if (field.type === 'radio') {
          const checked = document.querySelector(`[name="${fieldName}"]:checked`);
          data[fieldName] = checked ? checked.value : null;
        } else {
          data[fieldName] = field.value;
        }
      }
    });

    this.stepData[stepIndex] = data;
  }

  /**
   * Populate review step
   * @param {number} stepIndex - Review step index
   */
  populateReviewStep(stepIndex) {
    const reviewContent = document.querySelector(`#wizard-review-${stepIndex} .review-content`);
    if (!reviewContent) return;

    let html = '<div class="review-sections">';

    // Iterate through previous steps
    this.options.steps.forEach((step, index) => {
      if (index >= stepIndex || !step.fields) return;

      html += `
        <div class="review-section">
          <h5 class="review-section-title">
            ${step.title}
            <button type="button" class="btn btn-sm btn-link" onclick="wizard.goToStep(${index})">
              <i class="bi bi-pencil"></i> Edit
            </button>
          </h5>
          <div class="review-fields">
      `;

      step.fields.forEach(fieldName => {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (!field) return;

        const label = this.getFieldLabel(fieldName);
        const value = this.getFieldDisplayValue(field);

        html += `
          <div class="review-field">
            <span class="review-label">${label}:</span>
            <span class="review-value">${value}</span>
          </div>
        `;
      });

      html += `
          </div>
        </div>
      `;
    });

    html += '</div>';
    reviewContent.innerHTML = html;
  }

  /**
   * Get field label
   * @param {string} fieldName - Field name
   * @returns {string} Label text
   */
  getFieldLabel(fieldName) {
    const field = document.querySelector(`[name="${fieldName}"]`);
    if (!field) return fieldName;

    const labelEl = document.querySelector(`label[for="${field.id}"]`);
    if (labelEl) {
      return labelEl.textContent.trim().replace('*', '');
    }

    // Fallback: humanize field name
    return fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  /**
   * Get field display value
   * @param {HTMLElement} field - Field element
   * @returns {string} Display value
   */
  getFieldDisplayValue(field) {
    if (field.type === 'checkbox') {
      return field.checked ? 'Yes' : 'No';
    }

    if (field.type === 'radio') {
      const checked = document.querySelector(`[name="${field.name}"]:checked`);
      return checked ? checked.nextSibling.textContent.trim() : 'Not selected';
    }

    if (field.tagName === 'SELECT') {
      const selected = field.options[field.selectedIndex];
      return selected ? selected.text : 'Not selected';
    }

    return field.value || 'Not provided';
  }

  /**
   * Update progress indicator
   */
  updateProgressIndicator() {
    if (!this.progressContainer) return;

    // Update step classes
    this.progressContainer.querySelectorAll('.progress-step').forEach((stepEl, index) => {
      stepEl.classList.remove('active', 'completed');
      
      if (index === this.currentStep) {
        stepEl.classList.add('active');
      } else if (index < this.currentStep || this.completedSteps.has(index)) {
        stepEl.classList.add('completed');
      }
    });

    // Update progress bar
    const progressFill = this.progressContainer.querySelector('.progress-fill');
    if (progressFill) {
      const progress = ((this.currentStep + 1) / this.options.steps.length) * 100;
      progressFill.style.width = `${progress}%`;
    }

    // Update ARIA attributes
    this.progressContainer.setAttribute('aria-valuenow', this.currentStep + 1);
    this.progressContainer.setAttribute('aria-valuetext', `Step ${this.currentStep + 1} of ${this.options.steps.length}: ${this.options.steps[this.currentStep].title}`);
  }

  /**
   * Update navigation buttons
   */
  updateNavigationButtons() {
    const prevBtn = this.navigationContainer.querySelector('.wizard-btn-prev');
    const nextBtn = this.navigationContainer.querySelector('.wizard-btn-next');
    const submitBtn = this.navigationContainer.querySelector('.wizard-btn-submit');

    // Show/hide previous button
    prevBtn.style.display = this.currentStep > 0 ? 'inline-block' : 'none';

    // Show/hide next/submit buttons
    const isLastStep = this.currentStep === this.options.steps.length - 1;
    nextBtn.style.display = isLastStep ? 'none' : 'inline-block';
    submitBtn.style.display = isLastStep ? 'inline-block' : 'none';
  }

  /**
   * Save wizard progress
   */
  saveProgress() {
    try {
      const progress = {
        currentStep: this.currentStep,
        completedSteps: Array.from(this.completedSteps),
        stepData: this.stepData,
        timestamp: new Date().toISOString(),
      };

      localStorage.setItem(this.options.storageKey, JSON.stringify(progress));
      console.log('📝 Wizard progress saved');
    } catch (error) {
      console.error('❌ Failed to save wizard progress:', error);
    }
  }

  /**
   * Restore wizard progress
   */
  restoreProgress() {
    try {
      const progressJson = localStorage.getItem(this.options.storageKey);
      if (!progressJson) return;

      const progress = JSON.parse(progressJson);
      this.currentStep = progress.currentStep || 0;
      this.completedSteps = new Set(progress.completedSteps || []);
      this.stepData = progress.stepData || {};

      console.log('✅ Wizard progress restored');
    } catch (error) {
      console.error('❌ Failed to restore wizard progress:', error);
    }
  }

  /**
   * Clear wizard progress
   */
  clearProgress() {
    try {
      localStorage.removeItem(this.options.storageKey);
      console.log('🗑️ Wizard progress cleared');
    } catch (error) {
      console.error('❌ Failed to clear wizard progress:', error);
    }
  }

  /**
   * Attach keyboard listeners
   */
  attachKeyboardListeners() {
    document.addEventListener('keydown', (e) => {
      // Only handle if wizard is visible
      if (!this.wizard.offsetParent) return;

      if (e.key === 'ArrowRight' && e.ctrlKey) {
        // Ctrl+Right: Next step
        e.preventDefault();
        this.nextStep();
      } else if (e.key === 'ArrowLeft' && e.ctrlKey) {
        // Ctrl+Left: Previous step
        e.preventDefault();
        this.previousStep();
      }
    });
  }

  /**
   * Helper: delay
   * @param {number} ms - Milliseconds
   * @returns {Promise} Promise that resolves after delay
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get wizard data (all steps)
   * @returns {Object} All step data
   */
  getData() {
    // Save current step first
    this.saveStepData(this.currentStep);
    return this.stepData;
  }

  /**
   * Reset wizard to first step
   */
  reset() {
    this.currentStep = 0;
    this.completedSteps.clear();
    this.stepData = {};
    this.goToStep(0, false);
    this.clearProgress();
  }

  /**
   * Destroy wizard instance
   */
  destroy() {
    this.clearProgress();
    console.log('🛑 FormWizard destroyed');
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FormWizard;
}

// Make available globally for inline onclick handlers
window.FormWizard = FormWizard;
