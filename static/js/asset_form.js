// --- Image preview logic ---
const imageInput = document.getElementById('id_images');
const preview = document.getElementById('image-preview');
if (imageInput) {
    imageInput.addEventListener('change', function(e) {
        const [file] = imageInput.files;
        if (file) {
            preview.src = URL.createObjectURL(file);
            preview.classList.remove('d-none');
        } else {
            preview.classList.add('d-none');
        }
    });
}

// --- Dynamic Fields AJAX Logic ---
const categorySelect = document.getElementById('id_category');
const dynamicFieldsContainer = document.getElementById('dynamic-fields-container');

function sanitizeHTML(str) {
    const temp = document.createElement('div');
    temp.textContent = str;
    return temp.innerHTML;
}

function showDynamicFieldsLoading() {
    dynamicFieldsContainer.innerHTML = '<div class="d-flex align-items-center justify-content-center py-3"><div class="spinner-border text-primary me-2" role="status" aria-label="Loading"></div> <span>Loading fields...</span></div>';
}

function renderDynamicFields(fields) {
    if (!fields || Object.keys(fields).length === 0) {
        dynamicFieldsContainer.innerHTML = '<div class="alert alert-info mb-0">No additional fields for this category.</div>';
        return;
    }
    let html = '<div class="card mb-3"><div class="card-header bg-info text-dark">Category Fields</div><div class="card-body p-0"><table class="table table-bordered table-sm align-middle mb-0" style="background:rgba(255,255,255,0.7);"><tbody>';
    for (const [key, field] of Object.entries(fields)) {
        const fieldId = `id_dyn_${sanitizeHTML(key)}`;
        const required = field.required ? 'required' : '';
        const requiredMark = field.required ? ' <span class="text-danger">*</span>' : '';
        let input = '';
        if (field.type === 'text') {
            input = `<input type="text" name="dyn_${sanitizeHTML(key)}" id="${fieldId}" class="form-control" ${required} autocomplete="off">`;
        } else if (field.type === 'number') {
            input = `<input type="number" name="dyn_${sanitizeHTML(key)}" id="${fieldId}" class="form-control" ${required} step="any" autocomplete="off">`;
        } else if (field.type === 'date') {
            input = `<input type="date" name="dyn_${sanitizeHTML(key)}" id="${fieldId}" class="form-control" ${required} autocomplete="off">`;
        } else {
            input = `<input type="text" name="dyn_${sanitizeHTML(key)}" id="${fieldId}" class="form-control" ${required} autocomplete="off">`;
        }
        html += `<tr><th style="width:30%" class="text-end">${sanitizeHTML(field.label)}${requiredMark}</th><td>${input}</td></tr>`;
    }
    html += '</tbody></table></div></div>';
    dynamicFieldsContainer.innerHTML = html;
}

function fetchAndRenderDynamicFields(categoryId) {
    if (!categoryId) {
        dynamicFieldsContainer.innerHTML = '';
        return;
    }
    showDynamicFieldsLoading();
    fetch(`/api/dynamic-fields/?category_id=${encodeURIComponent(categoryId)}`)
        .then(res => res.json())
        .then(data => {
            console.log('Dynamic fields API response:', data); // DEBUG
            if (data.success) {
                renderDynamicFields(data.fields);
            } else {
                dynamicFieldsContainer.innerHTML = '<div class="alert alert-warning mb-0">No fields found for this category.</div>';
            }
        })
        .catch((err) => {
            console.error('Dynamic fields AJAX error:', err); // DEBUG
            dynamicFieldsContainer.innerHTML = '<div class="alert alert-danger mb-0">Error loading fields. Please try again.</div>';
        });
}

if (categorySelect) {
    // Initial load (for edit forms)
    if (categorySelect.value) {
        fetchAndRenderDynamicFields(categorySelect.value);
    }
    categorySelect.addEventListener('change', function() {
        fetchAndRenderDynamicFields(this.value);
    });
}

// --- Assigned To: Searchable Dropdown (simple, native) ---
(function() {
    const assignedTo = document.getElementById('id_assigned_to');
    if (assignedTo) {
        assignedTo.setAttribute('autocomplete', 'off');
        // Optionally, implement a search/filter for large user lists
    }
})();

// Get user role from data attribute (CSP-compliant)
var userRoleElem = document.getElementById('user-role');
var userRole = userRoleElem ? userRoleElem.getAttribute('data-role') : '';

// --- Custom Add User Modal Logic (Admin Only) ---
if (userRole === 'admin') {
    const openAddUserModalBtn = document.getElementById('openAddUserModal');
    const addUserModalCustom = document.getElementById('addUserModalCustom');
    const closeAddUserModalBtn = document.getElementById('closeAddUserModal');
    openAddUserModalBtn.addEventListener('click', () => {
      addUserModalCustom.classList.add('active');
      addUserModalCustom.focus();
    });
    closeAddUserModalBtn.addEventListener('click', () => {
      addUserModalCustom.classList.remove('active');
    });
    addUserModalCustom.addEventListener('click', (e) => {
      if (e.target === addUserModalCustom) {
        addUserModalCustom.classList.remove('active');
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && addUserModalCustom.classList.contains('active')) {
        addUserModalCustom.classList.remove('active');
      }
    });
    const addUserForm = document.getElementById('add-user-form');
    const addUserErrors = document.getElementById('add-user-errors');
    const addUserSuccess = document.getElementById('add-user-success');
    addUserForm.addEventListener('submit', function(e) {
        e.preventDefault();
        addUserErrors.classList.add('d-none');
        addUserSuccess.classList.add('d-none');
        const formData = new FormData(addUserForm);
        fetch('/api/users/create/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                addUserSuccess.textContent = 'User created successfully!';
                addUserSuccess.classList.remove('d-none');
                // Add new user to dropdown
                const assignedTo = document.getElementById('id_assigned_to');
                const opt = document.createElement('option');
                opt.value = data.user.id;
                opt.textContent = data.user.display;
                assignedTo.appendChild(opt);
                assignedTo.value = data.user.id;
                // Close modal after short delay
                setTimeout(() => {
                    addUserModalCustom.classList.remove('active');
                    addUserForm.reset();
                    addUserSuccess.classList.add('d-none');
                }, 1200);
            } else {
                let errMsg = '';
                if (data.errors) {
                    for (const [field, errs] of Object.entries(data.errors)) {
                        errMsg += `<strong>${sanitizeHTML(field)}:</strong> ${sanitizeHTML(errs.join(' '))}<br>`;
                    }
                } else {
                    errMsg = 'Unknown error.';
                }
                addUserErrors.innerHTML = errMsg;
                addUserErrors.classList.remove('d-none');
            }
        })
        .catch(() => {
            addUserErrors.textContent = 'Error creating user. Please try again.';
            addUserErrors.classList.remove('d-none');
        });
    });
} 