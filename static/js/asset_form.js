(function () {
  'use strict';

  const page = document.querySelector('.asset-form-page');
  const form = document.getElementById('assetForm');
  if (!page || !form) return;

  const category = form.querySelector('#id_category');
  const branch = form.querySelector('#id_branch');
  const assignee = form.querySelector('#id_assigned_to');
  const categoryContainer = document.getElementById('category-fields-container');
  const categoryEmpty = document.getElementById('category-fields-empty');
  const categoryStatus = document.getElementById('category-fields-status');
  const duplicateResults = document.getElementById('duplicate-detection-results');
  const submitButton = document.getElementById('asset-submit');
  const dynamicCache = new Map();
  let duplicateTimer = null;
  let duplicateRequest = null;
  let hasBlockingDuplicates = false;

  function fieldValueMap() {
    const values = {};
    categoryContainer.querySelectorAll('[name^="dyn_"]').forEach((field) => {
      if (field.type === 'file') return;
      values[field.name] = field.value;
    });
    return values;
  }

  function createDynamicField(key, definition, value) {
    const wrapper = document.createElement('div');
    wrapper.className = 'ui-form-field';
    const name = 'dyn_' + key;
    const id = 'id_' + name;
    const label = document.createElement('label');
    label.className = 'form-label';
    label.htmlFor = id;
    label.textContent = definition.label || key.replaceAll('_', ' ');

    if (definition.required) {
      const required = document.createElement('span');
      required.setAttribute('aria-hidden', 'true');
      required.textContent = ' *';
      label.appendChild(required);
    }

    let control;
    if (definition.type === 'textarea') {
      control = document.createElement('textarea');
      control.rows = 3;
      control.className = 'form-control';
    } else if (definition.type === 'select') {
      control = document.createElement('select');
      control.className = 'form-select';
      const empty = document.createElement('option');
      empty.value = '';
      empty.textContent = '-- Select --';
      control.appendChild(empty);
      const options = Array.isArray(definition.options)
        ? definition.options.map((option) => [option, option])
        : Object.entries(definition.options || {});
      options.forEach(([optionValue, optionLabel]) => {
        const option = document.createElement('option');
        option.value = optionValue;
        option.textContent = optionLabel;
        control.appendChild(option);
      });
    } else {
      control = document.createElement('input');
      control.type = definition.type === 'number' || definition.type === 'date'
        ? definition.type
        : definition.type === 'file' ? 'file' : 'text';
      control.className = 'form-control';
    }

    control.id = id;
    control.name = name;
    control.required = Boolean(definition.required);
    if (definition.max_length) control.maxLength = Number(definition.max_length);
    if (definition.min_value !== null && definition.min_value !== undefined) control.min = definition.min_value;
    if (definition.max_value !== null && definition.max_value !== undefined) control.max = definition.max_value;
    if (value !== undefined && control.type !== 'file') control.value = value;

    wrapper.append(label, control);
    if (definition.help_text) {
      const help = document.createElement('div');
      help.className = 'form-text';
      help.id = id + '_helptext';
      help.textContent = definition.help_text;
      control.setAttribute('aria-describedby', help.id);
      wrapper.appendChild(help);
    }
    return wrapper;
  }

  function appendWarrantyFields(values) {
    if (!categoryContainer.querySelector('[name="dyn_warranty_expiry"]')) {
      categoryContainer.appendChild(createDynamicField('warranty_expiry', {
        type: 'date', label: 'Warranty Expiry (Optional)', required: false
      }, values.dyn_warranty_expiry));
    }
    if (!categoryContainer.querySelector('[name="dyn_warranty_provider"]')) {
      categoryContainer.appendChild(createDynamicField('warranty_provider', {
        type: 'text', label: 'Warranty Provider (Optional)', required: false
      }, values.dyn_warranty_provider));
    }
  }

  async function loadCategoryFields() {
    if (!category || !categoryContainer) return;
    const previousCategory = category.dataset.previousValue || '';
    if (previousCategory) dynamicCache.set(previousCategory, fieldValueMap());
    const categoryId = category.value;
    category.dataset.previousValue = categoryId;
    hasBlockingDuplicates = false;
    clearDuplicateFeedback();

    if (!categoryId) {
      categoryContainer.replaceChildren();
      categoryEmpty.classList.remove('d-none');
      categoryStatus.textContent = 'No category selected.';
      return;
    }

    categoryStatus.textContent = 'Loading category fields.';
    categoryContainer.setAttribute('aria-busy', 'true');
    const savedValues = dynamicCache.get(categoryId) || {};
    try {
      const url = new URL(page.dataset.dynamicFieldsUrl, window.location.origin);
      url.searchParams.set('category_id', categoryId);
      const response = await fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      if (!response.ok) throw new Error('Unable to load category fields.');
      const payload = await response.json();
      if (!payload.success) throw new Error(payload.error || 'Unable to load category fields.');

      categoryContainer.replaceChildren();
      Object.entries(payload.fields || {}).forEach(([key, definition]) => {
        categoryContainer.appendChild(createDynamicField(key, definition, savedValues['dyn_' + key]));
      });
      appendWarrantyFields(savedValues);
      categoryEmpty.classList.toggle('d-none', categoryContainer.children.length > 0);
      categoryStatus.textContent = 'Category fields updated.';
    } catch (error) {
      categoryStatus.textContent = 'Category fields could not be loaded. Select the category again or submit to see server validation.';
      categoryEmpty.textContent = 'Additional fields are temporarily unavailable. Your core form remains usable.';
      categoryEmpty.classList.remove('d-none');
    } finally {
      categoryContainer.removeAttribute('aria-busy');
    }
  }

  function filterAssignees() {
    if (!branch || !assignee) return;
    const branchId = branch.value;
    Array.from(assignee.options).forEach((option, index) => {
      if (index === 0) return;
      const branchIds = (option.dataset.branchIds || '').split(',').filter(Boolean);
      const allowed = !branchId || branchIds.length === 0 || branchIds.includes(branchId);
      option.hidden = !allowed;
      option.disabled = !allowed;
    });
    if (assignee.selectedOptions[0] && assignee.selectedOptions[0].disabled) {
      assignee.value = '';
    }
  }

  function updateStatusPanels() {
    const status = form.querySelector('#id_status');
    if (!status || status.type === 'hidden') return;
    form.querySelectorAll('[data-status-panel]').forEach((panel) => {
      const visible = panel.dataset.statusPanel.split(',').includes(status.value);
      panel.hidden = !visible;
      panel.querySelectorAll('input, select, textarea').forEach((control) => {
        control.disabled = !visible;
      });
    });
  }

  function updateMaintenanceState() {
    const toggle = form.querySelector('#id_maintenance_enabled');
    const interval = form.querySelector('#id_maintenance_interval_days');
    if (!toggle || !interval) return;
    interval.closest('.ui-form-field')?.classList.toggle('opacity-50', !toggle.checked);
    interval.setAttribute('aria-disabled', String(!toggle.checked));
  }

  function clearDuplicateFeedback() {
    duplicateResults.classList.add('d-none');
    duplicateResults.classList.remove('asset-duplicate-results--danger');
    duplicateResults.replaceChildren();
    form.querySelectorAll('.is-invalid[data-duplicate-invalid]').forEach((field) => {
      field.classList.remove('is-invalid');
      delete field.dataset.duplicateInvalid;
    });
  }

  function renderDuplicateFeedback(payload) {
    clearDuplicateFeedback();
    hasBlockingDuplicates = Boolean(payload.has_blocking_errors);
    if (!hasBlockingDuplicates && !payload.has_warnings) return;

    duplicateResults.classList.remove('d-none');
    duplicateResults.classList.toggle('asset-duplicate-results--danger', hasBlockingDuplicates);
    const heading = document.createElement('h2');
    heading.textContent = hasBlockingDuplicates
      ? 'Resolve duplicate identifiers before saving'
      : 'Review possible matching assets';
    duplicateResults.appendChild(heading);
    const list = document.createElement('ul');

    Object.entries(payload.hard_constraint_errors || {}).forEach(([fieldName, errors]) => {
      const control = form.querySelector('[name="' + fieldName + '"]') ||
        form.querySelector('[name="dyn_' + fieldName + '"]');
      if (control) {
        control.classList.add('is-invalid');
        control.dataset.duplicateInvalid = 'true';
      }
      (Array.isArray(errors) ? errors : [errors]).forEach((message) => {
        const item = document.createElement('li');
        item.textContent = message;
        list.appendChild(item);
      });
    });

    (payload.potential_duplicates || []).slice(0, 5).forEach((match) => {
      const item = document.createElement('li');
      const identifier = match.asset_tag || match.serial_number || 'Existing asset';
      item.textContent = identifier + ' — ' + match.category + ', ' + match.similarity_score + '% similarity';
      list.appendChild(item);
    });
    duplicateResults.appendChild(list);
  }

  function duplicatePayload() {
    const payload = {
      serial_number: form.elements.serial_number?.value || '',
      asset_tag: form.elements.asset_tag?.value || '',
      qr_string: form.elements.qr_string?.value || '',
      category_id: category?.value || '',
      exclude_asset_id: page.dataset.excludeAssetId || ''
    };
    categoryContainer.querySelectorAll('[name^="dyn_"]').forEach((field) => {
      if (field.type !== 'file') payload[field.name] = field.value;
    });
    return payload;
  }

  async function checkDuplicates() {
    const payload = duplicatePayload();
    if (!payload.serial_number && !payload.asset_tag && !payload.qr_string) {
      hasBlockingDuplicates = false;
      clearDuplicateFeedback();
      return;
    }
    if (duplicateRequest) duplicateRequest.abort();
    duplicateRequest = new AbortController();
    try {
      const response = await fetch(page.dataset.duplicateUrl, {
        method: 'POST',
        credentials: 'same-origin',
        signal: duplicateRequest.signal,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': form.elements.csrfmiddlewaretoken.value,
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(payload)
      });
      if (!response.ok) return;
      renderDuplicateFeedback(await response.json());
    } catch (error) {
      if (error.name !== 'AbortError') {
        hasBlockingDuplicates = false;
        clearDuplicateFeedback();
      }
    }
  }

  function queueDuplicateCheck(event) {
    if (!event.target.matches('[name="serial_number"], [name="asset_tag"], [name="qr_string"], [name^="dyn_"]')) return;
    hasBlockingDuplicates = false;
    window.clearTimeout(duplicateTimer);
    duplicateTimer = window.setTimeout(checkDuplicates, 450);
  }

  function updateFileFeedback(event) {
    if (!event.target.matches('#id_images, #id_documents')) return;
    const files = Array.from(event.target.files || []);
    const feedback = document.getElementById('asset-file-feedback');
    feedback.textContent = files.length ? files.map((file) => file.name).join(', ') + ' selected.' : '';
  }

  category?.addEventListener('change', loadCategoryFields);
  branch?.addEventListener('change', filterAssignees);
  form.querySelector('#id_status')?.addEventListener('change', updateStatusPanels);
  form.querySelector('#id_maintenance_enabled')?.addEventListener('change', updateMaintenanceState);
  form.addEventListener('input', queueDuplicateCheck);
  form.addEventListener('change', (event) => {
    queueDuplicateCheck(event);
    updateFileFeedback(event);
  });
  form.addEventListener('submit', (event) => {
    if (!hasBlockingDuplicates) return;
    event.preventDefault();
    duplicateResults.focus();
    submitButton?.removeAttribute('aria-disabled');
  });

  if (category) category.dataset.previousValue = category.value;
  filterAssignees();
  updateStatusPanels();
  updateMaintenanceState();
  document.querySelector('.form-error-summary')?.focus();
})();
