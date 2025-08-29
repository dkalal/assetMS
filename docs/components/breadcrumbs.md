# Breadcrumbs Component Documentation

## Overview
The breadcrumbs component provides enterprise-grade navigation with robust error handling and accessibility support.

## Usage Examples

### 1. Simple Usage
```django
{% include 'components/breadcrumbs.html' with root_label='Dashboard' root_url='/dashboard/' current_label='Assets' %}
```

### 2. With Parent Navigation
```django
{% include 'components/breadcrumbs.html' with root_label='Dashboard' root_url='/dashboard/' parent_label='Assets' parent_url='/assets/' current_label='Detail' %}
```

### 3. From View Context
```django
{% include 'components/breadcrumbs.html' with crumbs=crumbs %}
```

Where `crumbs` is a list of dictionaries:
```python
crumbs = [
    {'label': 'Dashboard', 'url': '/dashboard/'},
    {'label': 'Assets', 'url': '/assets/'},
    {'label': 'Asset Detail'}  # No URL for current page
]
```

## Features

- **Fallback handling** for missing parameters
- **ARIA attributes** for accessibility
- **Bootstrap 5 compatible** styling
- **Enterprise-level error prevention**
- **Schema.org markup** for SEO
- **Responsive design**

## Accessibility

The component includes:
- `aria-label="Breadcrumb navigation"`
- `aria-current="page"` for active items
- Proper semantic HTML structure
- Schema.org breadcrumb markup

## Styling

Uses Bootstrap 5 classes:
- `.breadcrumb` for the container
- `.breadcrumb-item` for each navigation item
- `.active` for the current page

## Error Prevention

- Default values for all parameters
- Graceful handling of missing context
- No template recursion issues



