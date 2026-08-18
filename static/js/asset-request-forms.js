(function () {
  'use strict';
  const page = document.querySelector('.asset-request-page[data-dynamic-fields-url]');
  const category = document.getElementById('category_id');
  const container = document.getElementById('dynamic-fields-container');
  const empty = document.getElementById('dynamic-fields-empty');
  const status = document.getElementById('dynamic-fields-status');
  if (!page || !category || !container || !empty || !status) return;

  function createField(key, definition) {
    const wrapper = document.createElement('div');
    wrapper.className = 'ui-form-field';
    const id = 'field_' + key;
    const label = document.createElement('label');
    label.className = 'form-label';
    label.htmlFor = id;
    label.textContent = definition.label || key.replaceAll('_', ' ');
    if (definition.required) {
      const marker = document.createElement('span');
      marker.setAttribute('aria-hidden', 'true');
      marker.textContent = ' *';
      label.appendChild(marker);
    }
    const input = document.createElement('input');
    input.className = 'form-control';
    input.id = id;
    input.name = id;
    input.type = ['number', 'date'].includes(definition.type) ? definition.type : 'text';
    input.required = Boolean(definition.required);
    wrapper.append(label, input);
    return wrapper;
  }

  async function loadFields() {
    container.replaceChildren();
    if (!category.value) {
      empty.textContent = 'Select a category to see additional fields.';
      empty.classList.remove('d-none');
      status.textContent = 'No category selected.';
      return;
    }
    container.setAttribute('aria-busy', 'true');
    empty.classList.add('d-none');
    status.textContent = 'Loading category fields.';
    try {
      const url = new URL(page.dataset.dynamicFieldsUrl, window.location.origin);
      url.searchParams.set('category_id', category.value);
      const response = await fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      if (!response.ok) throw new Error();
      const payload = await response.json();
      Object.entries(payload.fields || {}).forEach(([key, definition]) => container.appendChild(createField(key, definition)));
      empty.textContent = 'No additional fields are required for this category.';
      empty.classList.toggle('d-none', container.children.length > 0);
      status.textContent = 'Category fields updated.';
    } catch (error) {
      empty.textContent = 'Additional fields could not be loaded. Select the category again before submitting.';
      empty.classList.remove('d-none');
      status.textContent = empty.textContent;
    } finally {
      container.removeAttribute('aria-busy');
    }
  }
  category.addEventListener('change', loadFields);
})();
