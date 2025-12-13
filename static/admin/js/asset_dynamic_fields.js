// Django admin: Dynamic fields for Asset based on category
(function() {
    function getDynamicFields(categoryId, callback) {
        if (!categoryId) return callback([]);
        fetch('/api/dynamic-fields/?category_id=' + encodeURIComponent(categoryId), {
            credentials: 'same-origin'
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                callback(data.fields);
            } else {
                callback([]);
            }
        })
        .catch(() => callback([]));
    }

    function renderDynamicFields(fields) {
        // Remove old dynamic fields
        document.querySelectorAll('.dynamic-field-row').forEach(el => el.remove());
        var form = document.querySelector('form#asset_form, form#asset_form_add, form#asset_form_change, form#asset_form .form-row');
        if (!form) form = document.querySelector('form');
        if (!form) return;
        var lastField = document.querySelector('[name="description"]');
        if (!lastField) return;
        Object.entries(fields).forEach(([key, field]) => {
            var row = document.createElement('div');
            row.className = 'form-row dynamic-field-row';
            var label = document.createElement('label');
            label.textContent = field.label || key;
            label.setAttribute('for', 'id_dyn_' + key);
            var input = document.createElement('input');
            input.type = field.type === 'number' ? 'number' : (field.type === 'date' ? 'date' : 'text');
            input.name = 'dyn_' + key;
            input.id = 'id_dyn_' + key;
            input.className = 'vTextField';
            if (field.required) input.required = true;
            row.appendChild(label);
            row.appendChild(input);
            lastField.parentNode.insertBefore(row, lastField.nextSibling);
        });
    }

    document.addEventListener('DOMContentLoaded', function() {
        var categorySelect = document.getElementById('id_category');
        if (!categorySelect) return;
        categorySelect.addEventListener('change', function() {
            getDynamicFields(this.value, function(fields) {
                renderDynamicFields(fields);
            });
        });
        // On page load, if category is selected, render fields
        if (categorySelect.value) {
            getDynamicFields(categorySelect.value, function(fields) {
                renderDynamicFields(fields);
            });
        }
    });
})(); 