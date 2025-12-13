/**
 * Phase 1: World-Class Asset Registration Features
 * 
 * Features:
 * 1. Auto-Save & Draft Management - Save form data every 30s to localStorage
 * 2. Duplicate Detection - Real-time check for similar assets
 * 3. Smart Auto-Complete - Intelligent field suggestions based on history
 * 
 * Inspired by: ServiceNow ITAM, IBM Maximo, SAP EAM, Snipe-IT
 * 
 * Design Principles:
 * - Simple & elegant (no over-engineering)
 * - Non-intrusive (doesn't break existing functionality)
 * - Performance-optimized (debounced, cached)
 * - Secure (CSRF, multi-tenancy)
 */

class AssetFormPhase1Enhancement {
    constructor(baseForm) {
        this.baseForm = baseForm; // Reference to AssetRegistrationForm instance
        this.form = baseForm.form;
        this.categorySelect = baseForm.categorySelect;
        this.branchSelect = document.getElementById('id_branch'); // CRITICAL: Initialize branch field
        this.dynamicFieldsContainer = baseForm.dynamicFieldsContainer;
        
        // CRITICAL: Validate we have the correct form (asset registration, not navbar search)
        if (!this.validateForm()) {
            console.error('❌ Phase 1: Invalid form reference. Aborting initialization.');
            return;
        }
        
        // Auto-save configuration
        this.autoSaveInterval = 30000; // 30 seconds
        this.autoSaveTimer = null;
        this.draftKey = 'asset_form_draft';
        this.lastSavedData = null;
        
        // Duplicate detection configuration
        this.duplicateCheckDebounce = 1000; // 1 second
        this.duplicateCheckTimer = null;
        this.lastDuplicateCheck = null;
        
        // Smart suggestions configuration
        this.suggestionCache = {}; // Cache suggestions per field
        this.suggestionDebounce = 300; // 300ms
        
        console.log('🚀 Phase 1 Enhancement - Initialized');
        this.init();
    }
    
    validateForm() {
        // Ensure we have the asset registration form, not navbar search or other forms
        if (!this.form) {
            console.error('❌ Phase 1: Form reference is null');
            return false;
        }
        
        // Check for required elements that only exist in asset registration form
        const hasCategory = this.form.querySelector('#id_category') !== null;
        const hasStatus = this.form.querySelector('#id_status') !== null;
        const hasDynamicFields = this.form.querySelector('#dynamic-fields-container') !== null;
        
        if (!hasCategory || !hasStatus || !hasDynamicFields) {
            console.error('❌ Phase 1: Form does not appear to be asset registration form');
            console.error('  - Has category field:', hasCategory);
            console.error('  - Has status field:', hasStatus);
            console.error('  - Has dynamic fields container:', hasDynamicFields);
            return false;
        }
        
        // Additional check: form should have method="post" and enctype for file uploads
        const method = this.form.getAttribute('method');
        const enctype = this.form.getAttribute('enctype');
        
        if (method?.toLowerCase() !== 'post') {
            console.error('❌ Phase 1: Form method is not POST (found:', method, ')');
            return false;
        }
        
        console.log('✅ Phase 1: Form validation passed - correct asset registration form');
        return true;
    }
    
    init() {
        // Feature 1: Auto-Save & Draft Management
        this.initAutoSave();
        
        // Feature 2: Duplicate Detection
        this.initDuplicateDetection();
        
        // Feature 3: Smart Auto-Complete
        this.initSmartSuggestions();
        
        // Add UI indicators
        this.addPhase1UI();
    }
    
    // ==========================================
    // FEATURE 1: AUTO-SAVE & DRAFT MANAGEMENT
    // ==========================================
    
    initAutoSave() {
        // Check for existing draft on page load
        this.checkForDraft();
        
        // Start auto-save timer
        this.startAutoSave();
        
        // Save on form change (debounced)
        this.form.addEventListener('input', () => {
            this.debouncedAutoSave();
        });
        
        // Clear draft on successful submission
        this.form.addEventListener('submit', () => {
            setTimeout(() => {
                this.clearDraft();
            }, 1000);
        });
        
        console.log('✅ Auto-Save enabled (every 30s)');
    }
    
    startAutoSave() {
        this.autoSaveTimer = setInterval(() => {
            this.saveDraft();
        }, this.autoSaveInterval);
    }
    
    debouncedAutoSave() {
        clearTimeout(this.autoSaveDebounceTimer);
        this.autoSaveDebounceTimer = setTimeout(() => {
            this.saveDraft();
        }, 2000); // Save 2s after last input
    }
    
    saveDraft() {
        try {
            const formData = this.getFormData();
            
            // Don't save if form is empty
            if (Object.keys(formData).length === 0) {
                return;
            }
            
            // Check if data has changed
            const currentDataString = JSON.stringify(formData);
            if (currentDataString === this.lastSavedData) {
                return; // No changes
            }
            
            const draft = {
                timestamp: new Date().toISOString(),
                category_id: this.categorySelect?.value || null,
                branch_id: this.branchSelect?.value || null,  // Include branch
                data: formData
            };
            
            localStorage.setItem(this.draftKey, JSON.stringify(draft));
            this.lastSavedData = currentDataString;
            
            console.log('💾 Draft auto-saved');
            this.showAutoSaveIndicator('saved');
        } catch (error) {
            console.error('❌ Failed to save draft:', error);
            this.showAutoSaveIndicator('error');
        }
    }
    
    checkForDraft() {
        try {
            const draftString = localStorage.getItem(this.draftKey);
            if (!draftString) return;
            
            const draft = JSON.parse(draftString);
            const draftAge = Date.now() - new Date(draft.timestamp).getTime();
            
            // Only restore drafts less than 24 hours old
            if (draftAge > 24 * 60 * 60 * 1000) {
                this.clearDraft();
                return;
            }
            
            // Show restore prompt
            this.showDraftRestorePrompt(draft);
        } catch (error) {
            console.warn('⚠️ Failed to check draft:', error);
        }
    }
    
    showDraftRestorePrompt(draft) {
        const draftDate = new Date(draft.timestamp).toLocaleString();
        
        const alertHTML = `
            <div class="alert alert-info alert-dismissible fade show shadow-sm" role="alert" id="draft-restore-alert">
                <div class="d-flex align-items-start">
                    <i class="bi bi-clock-history me-3 fs-4"></i>
                    <div class="flex-grow-1">
                        <h6 class="alert-heading mb-2">
                            <i class="bi bi-magic me-1"></i>
                            Draft Found!
                        </h6>
                        <p class="mb-2">
                            We found an unsaved draft from <strong>${draftDate}</strong>.
                            Would you like to restore it?
                        </p>
                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-sm btn-primary" id="restore-draft-btn">
                                <i class="bi bi-arrow-clockwise me-1"></i>
                                Restore Draft
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-secondary" id="discard-draft-btn">
                                <i class="bi bi-trash me-1"></i>
                                Discard
                            </button>
                        </div>
                    </div>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        this.form.insertAdjacentHTML('beforebegin', alertHTML);
        
        // Restore button
        document.getElementById('restore-draft-btn')?.addEventListener('click', () => {
            this.restoreFormDraft(draft);
            document.getElementById('draft-restore-alert')?.remove();
        });
        
        // Discard button
        document.getElementById('discard-draft-btn')?.addEventListener('click', () => {
            this.clearDraft();
            document.getElementById('draft-restore-alert')?.remove();
        });
    }
    
    async restoreFormDraft(draft) {
        try {
            console.log('🔄 Restoring draft...', draft);
            
            // Step 1: Restore branch FIRST (critical for multi-tenancy validation)
            if (draft.data.branch && this.branchSelect) {
                this.branchSelect.value = draft.data.branch;
                this.branchSelect.dispatchEvent(new Event('change', { bubbles: true }));
                console.log('✅ Branch restored:', draft.data.branch);
            }
            
            // Step 2: Restore category (triggers dynamic fields load)
            if (draft.data.category && this.categorySelect) {
                this.categorySelect.value = draft.data.category;
                this.categorySelect.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Wait for dynamic fields to load
                await this.waitForDynamicFields(1000);
            }
            
            // Step 3: Restore all other fields (including dynamic fields)
            this.setFormData(draft.data);
            
            // Step 4: Success feedback
            this.showToast('✅ Draft restored successfully!', 'success');
            console.log('✅ Draft restored successfully');
            
        } catch (error) {
            console.error('❌ Failed to restore draft:', error);
            this.showToast('❌ Failed to restore draft', 'danger');
        }
    }
    
    /**
     * Wait for dynamic fields to be rendered in the DOM
     * @param {number} maxWait - Maximum time to wait in milliseconds
     * @returns {Promise<boolean>} - True if fields loaded, false if timeout
     */
    waitForDynamicFields(maxWait = 1000) {
        return new Promise((resolve) => {
            const startTime = Date.now();
            const checkInterval = 100;
            
            const checkFields = () => {
                // Check if dynamic fields container has content
                const container = document.getElementById('dynamic-fields-container');
                const hasFields = container && container.children.length > 0;
                
                if (hasFields) {
                    console.log('✅ Dynamic fields loaded');
                    resolve(true);
                } else if (Date.now() - startTime > maxWait) {
                    console.warn('⚠️ Timeout waiting for dynamic fields');
                    resolve(false);
                } else {
                    setTimeout(checkFields, checkInterval);
                }
            };
            
            checkFields();
        });
    }
    
    getFormData() {
        const data = {};
        const formData = new FormData(this.form);
        
        for (let [key, value] of formData.entries()) {
            // Skip empty values and files
            if (value && typeof value === 'string') {
                data[key] = value;
            }
        }
        
        // CRITICAL: Include branch field
        if (this.branchSelect && this.branchSelect.value) {
            data['branch'] = this.branchSelect.value;
        }
        
        // Include category for restoration
        if (this.categorySelect && this.categorySelect.value) {
            data['category'] = this.categorySelect.value;
        }
        
        return data;
    }
    
    setFormData(data) {
        if (!data || typeof data !== 'object') {
            console.warn('⚠️ Invalid data for restoration');
            return;
        }
        
        let restoredCount = 0;
        let failedFields = [];
        
        Object.entries(data).forEach(([key, value]) => {
            const input = this.form.querySelector(`[name="${key}"]`);
            
            if (!input) {
                // Field doesn't exist (might be dynamic field not loaded yet)
                if (!key.startsWith('csrf')) {
                    failedFields.push(key);
                }
                return;
            }
            
            if (!value) {
                return; // Skip empty values
            }
            
            try {
                // Set value based on input type
                if (input.type === 'checkbox') {
                    input.checked = value === 'true' || value === true;
                } else if (input.type === 'radio') {
                    if (input.value === value) {
                        input.checked = true;
                    }
                } else {
                    input.value = value;
                }
                
                // Trigger change event for dropdowns
                if (input.tagName === 'SELECT') {
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
                
                // Visual feedback
                input.classList.add('is-valid');
                setTimeout(() => input.classList.remove('is-valid'), 2000);
                
                restoredCount++;
            } catch (error) {
                console.error(`❌ Failed to restore field "${key}":`, error);
                failedFields.push(key);
            }
        });
        
        console.log(`✅ Restored ${restoredCount} fields`);
        if (failedFields.length > 0) {
            console.warn(`⚠️ Failed to restore fields:`, failedFields);
        }
    }
    
    clearDraft() {
        localStorage.removeItem(this.draftKey);
        this.lastSavedData = null;
        console.log('🗑️ Draft cleared');
    }
    
    showAutoSaveIndicator(status) {
        let indicator = document.getElementById('autosave-indicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'autosave-indicator';
            indicator.className = 'position-fixed bottom-0 end-0 m-3';
            indicator.style.zIndex = '10000';
            document.body.appendChild(indicator);
        }
        
        const icons = {
            saving: '<i class="bi bi-arrow-repeat spinner-border spinner-border-sm me-1"></i>',
            saved: '<i class="bi bi-check-circle-fill me-1"></i>',
            error: '<i class="bi bi-exclamation-triangle-fill me-1"></i>',
        };
        
        const colors = {
            saving: 'info',
            saved: 'success',
            error: 'warning',
        };
        
        const messages = {
            saving: 'Saving draft...',
            saved: 'Draft saved',
            error: 'Save failed',
        };
        
        indicator.innerHTML = `
            <div class="badge bg-${colors[status]} shadow-sm">
                ${icons[status]} ${messages[status]}
            </div>
        `;
        
        // Auto-hide after 3 seconds
        if (status !== 'saving') {
            setTimeout(() => {
                indicator.style.opacity = '0';
                setTimeout(() => {
                    indicator.innerHTML = '';
                    indicator.style.opacity = '1';
                }, 300);
            }, 3000);
        }
    }
    
    // ==========================================
    // FEATURE 2: DUPLICATE DETECTION
    // ==========================================
    
    initDuplicateDetection() {
        // Check for duplicates when dynamic fields change
        this.dynamicFieldsContainer.addEventListener('input', () => {
            this.debouncedDuplicateCheck();
        });
        
        // Also check when category changes
        this.categorySelect?.addEventListener('change', () => {
            this.debouncedDuplicateCheck();
        });
        
        console.log('✅ Duplicate Detection enabled');
    }
    
    debouncedDuplicateCheck() {
        clearTimeout(this.duplicateCheckTimer);
        this.duplicateCheckTimer = setTimeout(() => {
            this.checkForDuplicates();
        }, this.duplicateCheckDebounce);
    }
    
    async checkForDuplicates() {
        const categoryId = this.categorySelect?.value;
        if (!categoryId) return;
        
        try {
            // Get dynamic field values
            const dynamicData = {};
            const dynamicInputs = this.dynamicFieldsContainer.querySelectorAll('[name^="dyn_"]');
            
            dynamicInputs.forEach(input => {
                const key = input.name.replace('dyn_', '');
                const value = input.value.trim();
                if (value) {
                    dynamicData[key] = value;
                }
            });
            
            // Skip if no data to check
            if (Object.keys(dynamicData).length === 0) {
                this.hideDuplicateWarning();
                return;
            }
            
            // Check if data changed since last check
            const dataString = JSON.stringify(dynamicData);
            if (dataString === this.lastDuplicateCheck) {
                return;
            }
            this.lastDuplicateCheck = dataString;
            
            // Call API
            const params = new URLSearchParams({
                category_id: categoryId,
                dynamic_data: JSON.stringify(dynamicData),
            });
            
            const response = await fetch(`/assets/api/check-duplicate-assets/?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.duplicates && data.duplicates.length > 0) {
                this.showDuplicateWarning(data.duplicates);
            } else {
                this.hideDuplicateWarning();
            }
            
        } catch (error) {
            console.warn('⚠️ Duplicate check failed:', error);
        }
    }
    
    showDuplicateWarning(duplicates) {
        // Remove existing warning
        this.hideDuplicateWarning();
        
        const topDuplicate = duplicates[0];
        const matchingFields = topDuplicate.matching_fields.join(', ');
        
        const warningHTML = `
            <div class="alert alert-warning alert-dismissible fade show shadow-sm" role="alert" id="duplicate-warning">
                <div class="d-flex align-items-start">
                    <i class="bi bi-exclamation-triangle-fill me-3 fs-4"></i>
                    <div class="flex-grow-1">
                        <h6 class="alert-heading mb-2">
                            <i class="bi bi-copy me-1"></i>
                            Potential Duplicate Detected!
                        </h6>
                        <p class="mb-2">
                            Found <strong>${duplicates.length}</strong> similar asset(s) with 
                            <strong>${topDuplicate.similarity_score}% similarity</strong>.
                        </p>
                        <p class="mb-2 small">
                            <strong>Matching fields:</strong> ${matchingFields}
                        </p>
                        <button type="button" class="btn btn-sm btn-outline-warning" id="view-duplicates-btn">
                            <i class="bi bi-eye me-1"></i>
                            View Similar Assets
                        </button>
                    </div>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        this.dynamicFieldsContainer.insertAdjacentHTML('afterend', warningHTML);
        
        // View duplicates button
        document.getElementById('view-duplicates-btn')?.addEventListener('click', () => {
            this.showDuplicatesModal(duplicates);
        });
    }
    
    hideDuplicateWarning() {
        document.getElementById('duplicate-warning')?.remove();
    }
    
    showDuplicatesModal(duplicates) {
        const modalHTML = `
            <div class="modal fade" id="duplicatesModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-warning text-dark">
                            <h5 class="modal-title">
                                <i class="bi bi-copy me-2"></i>
                                Similar Assets Found
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p class="text-muted mb-3">
                                Review these similar assets before proceeding. You may be creating a duplicate.
                            </p>
                            <div class="list-group">
                                ${duplicates.map(dup => `
                                    <div class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-start">
                                            <div class="flex-grow-1">
                                                <h6 class="mb-1">
                                                    ${this.escapeHtml(dup.category)}
                                                    <span class="badge bg-${this.getStatusColor(dup.status)} ms-2">
                                                        ${this.escapeHtml(dup.status)}
                                                    </span>
                                                </h6>
                                                <p class="mb-1 small text-muted">
                                                    <i class="bi bi-calendar me-1"></i>
                                                    Created: ${new Date(dup.created_at).toLocaleDateString()}
                                                    ${dup.assigned_to ? `<i class="bi bi-person ms-2 me-1"></i>${this.escapeHtml(dup.assigned_to)}` : ''}
                                                </p>
                                                <p class="mb-0 small">
                                                    <strong>Matching:</strong> ${dup.matching_fields.join(', ')}
                                                </p>
                                            </div>
                                            <div class="text-end">
                                                <div class="badge bg-warning text-dark fs-6">
                                                    ${dup.similarity_score}%
                                                </div>
                                                <div class="mt-2">
                                                    <a href="/assets/${dup.uuid}/" target="_blank" class="btn btn-sm btn-outline-primary">
                                                        <i class="bi bi-box-arrow-up-right me-1"></i>
                                                        View
                                                    </a>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                Close
                            </button>
                            <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
                                Continue Anyway
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal
        document.getElementById('duplicatesModal')?.remove();
        
        // Add new modal
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('duplicatesModal'));
        modal.show();
        
        // Clean up on close
        document.getElementById('duplicatesModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    }
    
    // ==========================================
    // FEATURE 3: SMART AUTO-COMPLETE
    // ==========================================
    
    initSmartSuggestions() {
        // Add suggestions to text fields in dynamic fields
        const observer = new MutationObserver(() => {
            this.attachSuggestionsToFields();
        });
        
        observer.observe(this.dynamicFieldsContainer, {
            childList: true,
            subtree: true,
        });
        
        // Initial attachment
        this.attachSuggestionsToFields();
        
        console.log('✅ Smart Suggestions enabled');
    }
    
    attachSuggestionsToFields() {
        const textFields = this.dynamicFieldsContainer.querySelectorAll('input[type="text"][name^="dyn_"]');
        
        textFields.forEach(input => {
            // Skip if already attached
            if (input.dataset.suggestionsAttached) return;
            
            input.dataset.suggestionsAttached = 'true';
            
            // Add autocomplete attributes
            input.setAttribute('autocomplete', 'off');
            input.setAttribute('data-smart-suggest', 'true');
            
            // Create datalist for suggestions
            const fieldKey = input.name.replace('dyn_', '');
            const datalistId = `suggestions-${fieldKey}`;
            
            let datalist = document.getElementById(datalistId);
            if (!datalist) {
                datalist = document.createElement('datalist');
                datalist.id = datalistId;
                input.after(datalist);
            }
            
            input.setAttribute('list', datalistId);
            
            // Load suggestions on focus
            input.addEventListener('focus', () => {
                this.loadSuggestions(fieldKey, datalist);
            });
            
            // Reload on input (debounced)
            let debounceTimer;
            input.addEventListener('input', () => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.loadSuggestions(fieldKey, datalist, input.value);
                }, this.suggestionDebounce);
            });
        });
    }
    
    async loadSuggestions(fieldKey, datalist, query = '') {
        const categoryId = this.categorySelect?.value;
        if (!categoryId) return;
        
        // Check cache
        const cacheKey = `${categoryId}_${fieldKey}_${query}`;
        if (this.suggestionCache[cacheKey]) {
            this.renderSuggestions(datalist, this.suggestionCache[cacheKey]);
            return;
        }
        
        try {
            const params = new URLSearchParams({
                category_id: categoryId,
                field_key: fieldKey,
                limit: 10,
            });
            
            if (query) {
                params.append('query', query);
            }
            
            const response = await fetch(`/assets/api/smart-suggestions/?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.suggestions) {
                // Cache suggestions
                this.suggestionCache[cacheKey] = data.suggestions;
                
                // Render suggestions
                this.renderSuggestions(datalist, data.suggestions);
            }
            
        } catch (error) {
            console.warn('⚠️ Failed to load suggestions:', error);
        }
    }
    
    renderSuggestions(datalist, suggestions) {
        datalist.innerHTML = '';
        
        suggestions.forEach(suggestion => {
            const option = document.createElement('option');
            option.value = suggestion.value;
            option.textContent = `${suggestion.value} (used ${suggestion.count}x)`;
            datalist.appendChild(option);
        });
    }
    
    // ==========================================
    // UI ENHANCEMENTS
    // ==========================================
    
    addPhase1UI() {
        // Professional badge placement: Inside form, after CSRF token, before first field
        // This ensures badges are part of the form container, not floating at template root
        
        // Find the form's first child (usually CSRF token or non_field_errors)
        const firstFormChild = this.form.firstElementChild;
        
        if (!firstFormChild) {
            console.warn('⚠️ Phase 1: Cannot find form children for badge placement');
            return;
        }
        
        // Professional badge design with glassmorphism and subtle animations
        const badgesHTML = `
            <div class="phase1-feature-badges mb-4" id="phase1-badges">
                <div class="d-flex align-items-center gap-3 flex-wrap">
                    <div class="badge-label text-muted small fw-semibold">
                        <i class="bi bi-stars me-1"></i>
                        Enhanced Features:
                    </div>
                    <div class="d-flex gap-2 flex-wrap">
                        <span class="badge badge-phase1 badge-success" 
                              title="Form data is automatically saved every 30 seconds"
                              data-bs-toggle="tooltip">
                            <i class="bi bi-cloud-check me-1"></i>
                            Auto-Save
                        </span>
                        <span class="badge badge-phase1 badge-warning" 
                              title="Automatically detects similar assets to prevent duplicates"
                              data-bs-toggle="tooltip">
                            <i class="bi bi-shield-check me-1"></i>
                            Duplicate Detection
                        </span>
                        <span class="badge badge-phase1 badge-info" 
                              title="Smart field suggestions based on historical data"
                              data-bs-toggle="tooltip">
                            <i class="bi bi-magic me-1"></i>
                            Smart Suggestions
                        </span>
                    </div>
                </div>
            </div>
            
            <style>
                /* Phase 1 Badge Styling - Professional & Non-Intrusive */
                .phase1-feature-badges {
                    background: linear-gradient(135deg, rgba(0, 166, 235, 0.05) 0%, rgba(100, 204, 197, 0.05) 100%);
                    border: 1px solid rgba(0, 166, 235, 0.15);
                    border-radius: 12px;
                    padding: 0.875rem 1.25rem;
                    margin-top: 0.5rem;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
                    transition: all 0.3s ease;
                }
                
                .phase1-feature-badges:hover {
                    border-color: rgba(0, 166, 235, 0.25);
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                }
                
                .phase1-feature-badges .badge-label {
                    font-size: 0.8125rem;
                    letter-spacing: 0.3px;
                    color: #6c757d;
                    display: flex;
                    align-items: center;
                }
                
                .badge-phase1 {
                    font-size: 0.8125rem;
                    font-weight: 600;
                    padding: 0.5rem 0.875rem;
                    border-radius: 8px;
                    transition: all 0.2s ease;
                    cursor: help;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.25rem;
                }
                
                .badge-phase1:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
                }
                
                .badge-phase1.badge-success {
                    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                    color: white;
                }
                
                .badge-phase1.badge-warning {
                    background: linear-gradient(135deg, #ffc107 0%, #ffb300 100%);
                    color: #212529;
                }
                
                .badge-phase1.badge-info {
                    background: linear-gradient(135deg, #00A6EB 0%, #64CCC5 100%);
                    color: white;
                }
                
                .badge-phase1 i {
                    font-size: 0.875rem;
                }
                
                /* Responsive adjustments */
                @media (max-width: 768px) {
                    .phase1-feature-badges {
                        padding: 0.75rem 1rem;
                    }
                    
                    .phase1-feature-badges .badge-label {
                        width: 100%;
                        margin-bottom: 0.5rem;
                    }
                    
                    .badge-phase1 {
                        font-size: 0.75rem;
                        padding: 0.4rem 0.75rem;
                    }
                }
                
                /* Animation on page load */
                @keyframes fadeInUp {
                    from {
                        opacity: 0;
                        transform: translateY(10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                .phase1-feature-badges {
                    animation: fadeInUp 0.5s ease-out;
                }
            </style>
        `;
        
        // Insert badges after the first form child (CSRF token), before form fields
        if (!document.getElementById('phase1-badges')) {
            firstFormChild.insertAdjacentHTML('afterend', badgesHTML);
            
            // Initialize Bootstrap tooltips for badges
            this.initializeBadgeTooltips();
        }
    }
    
    initializeBadgeTooltips() {
        // Initialize Bootstrap 5 tooltips for badge hover effects
        try {
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
            }
        } catch (error) {
            console.warn('⚠️ Phase 1: Bootstrap tooltips not available', error);
        }
    }
    
    // ==========================================
    // UTILITY METHODS
    // ==========================================
    
    showToast(message, type = 'info') {
        // Use existing toast system if available
        if (window.showToast) {
            window.showToast(message, type);
            return;
        }
        
        // Fallback toast
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed bottom-0 end-0 m-3 shadow-lg`;
        toast.style.zIndex = '10000';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => toast.remove(), 3000);
    }
    
    escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(unsafe);
        return div.innerHTML;
    }
    
    getStatusColor(status) {
        const colors = {
            'active': 'success',
            'in_maintenance': 'warning',
            'retired': 'secondary',
            'lost': 'danger',
            'deleted': 'dark',
            'transferred': 'info',
        };
        return colors[status] || 'secondary';
    }
    
    destroy() {
        // Clean up timers
        if (this.autoSaveTimer) {
            clearInterval(this.autoSaveTimer);
        }
        if (this.duplicateCheckTimer) {
            clearTimeout(this.duplicateCheckTimer);
        }
        
        console.log('🛑 Phase 1 Enhancement - Destroyed');
    }
}

// Initialize Phase 1 enhancements when base form is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for base form to initialize
    const checkBaseForm = setInterval(() => {
        if (window.assetRegistrationForm) {
            clearInterval(checkBaseForm);
            
            console.log('🚀 Initializing Phase 1 Enhancements');
            window.assetFormPhase1 = new AssetFormPhase1Enhancement(window.assetRegistrationForm);
        }
    }, 100);
    
    // Timeout after 5 seconds
    setTimeout(() => {
        clearInterval(checkBaseForm);
    }, 5000);
});
