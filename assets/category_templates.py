"""
Category Templates for Multi-Tenancy Asset Management System
Provides pre-configured category templates with best-practice field configurations
"""

CATEGORY_TEMPLATES = {
    'it_equipment': {
        'name': 'IT Equipment',
        'icon': 'bi-laptop',
        'color': '#0d6efd',
        'description': 'Computers, laptops, servers, and IT hardware',
        'fields': [
            {
                'label': 'Serial Number',
                'key': 'serial_number',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., SN123456789',
                'help_text': 'Manufacturer serial number'
            },
            {
                'label': 'Model',
                'key': 'model',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., Dell Latitude 5520',
                'help_text': 'Device model name'
            },
            {
                'label': 'Manufacturer',
                'key': 'manufacturer',
                'type': 'text',
                'required': False,
                'placeholder': 'e.g., Dell, HP, Lenovo',
                'help_text': 'Equipment manufacturer'
            },
            {
                'label': 'Purchase Date',
                'key': 'purchase_date',
                'type': 'date',
                'required': False,
                'help_text': 'Date of purchase'
            },
            {
                'label': 'Warranty Expiry',
                'key': 'warranty_expiry',
                'type': 'date',
                'required': False,
                'help_text': 'Warranty expiration date'
            },
            {
                'label': 'Processor',
                'key': 'processor',
                'type': 'text',
                'required': False,
                'placeholder': 'e.g., Intel Core i7',
                'help_text': 'CPU specifications'
            },
            {
                'label': 'RAM (GB)',
                'key': 'ram_gb',
                'type': 'number',
                'required': False,
                'placeholder': 'e.g., 16',
                'help_text': 'Memory in gigabytes'
            },
            {
                'label': 'Storage (GB)',
                'key': 'storage_gb',
                'type': 'number',
                'required': False,
                'placeholder': 'e.g., 512',
                'help_text': 'Storage capacity'
            }
        ]
    },
    'vehicles': {
        'name': 'Vehicles',
        'icon': 'bi-truck',
        'color': '#198754',
        'description': 'Cars, trucks, vans, and company vehicles',
        'fields': [
            {
                'label': 'License Plate',
                'key': 'license_plate',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., ABC-1234',
                'help_text': 'Vehicle registration number'
            },
            {
                'label': 'VIN',
                'key': 'vin',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., 1HGBH41JXMN109186',
                'help_text': 'Vehicle Identification Number'
            },
            {
                'label': 'Make',
                'key': 'make',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., Toyota, Ford',
                'help_text': 'Vehicle manufacturer'
            },
            {
                'label': 'Model',
                'key': 'model',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., Camry, F-150',
                'help_text': 'Vehicle model'
            },
            {
                'label': 'Year',
                'key': 'year',
                'type': 'number',
                'required': True,
                'placeholder': 'e.g., 2023',
                'help_text': 'Manufacturing year'
            },
            {
                'label': 'Mileage',
                'key': 'mileage',
                'type': 'number',
                'required': False,
                'placeholder': 'e.g., 50000',
                'help_text': 'Current mileage in km'
            },
            {
                'label': 'Insurance Expiry',
                'key': 'insurance_expiry',
                'type': 'date',
                'required': False,
                'help_text': 'Insurance expiration date'
            },
            {
                'label': 'Next Service Date',
                'key': 'next_service',
                'type': 'date',
                'required': False,
                'help_text': 'Scheduled maintenance date'
            }
        ]
    },
    'furniture': {
        'name': 'Furniture',
        'icon': 'bi-house-door',
        'color': '#fd7e14',
        'description': 'Office furniture, desks, chairs, and fixtures',
        'fields': [
            {
                'label': 'Item Type',
                'key': 'item_type',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., Desk, Chair, Cabinet',
                'help_text': 'Type of furniture'
            },
            {
                'label': 'Material',
                'key': 'material',
                'type': 'text',
                'required': False,
                'placeholder': 'e.g., Wood, Metal, Plastic',
                'help_text': 'Primary material'
            },
            {
                'label': 'Color',
                'key': 'color',
                'type': 'text',
                'required': False,
                'placeholder': 'e.g., Black, Brown, White',
                'help_text': 'Furniture color'
            },
            {
                'label': 'Dimensions',
                'key': 'dimensions',
                'type': 'text',
                'required': False,
                'placeholder': 'e.g., 120x60x75 cm',
                'help_text': 'Length x Width x Height'
            },
            {
                'label': 'Purchase Date',
                'key': 'purchase_date',
                'type': 'date',
                'required': False,
                'help_text': 'Date of purchase'
            },
            {
                'label': 'Condition',
                'key': 'condition',
                'type': 'text',
                'required': False,
                'placeholder': 'e.g., New, Good, Fair',
                'help_text': 'Current condition'
            }
        ]
    },
    'electronics': {
        'name': 'Electronics',
        'icon': 'bi-phone',
        'color': '#6f42c1',
        'description': 'Phones, tablets, monitors, and electronic devices',
        'fields': [
            {
                'label': 'Device Type',
                'key': 'device_type',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., Smartphone, Tablet, Monitor',
                'help_text': 'Type of electronic device'
            },
            {
                'label': 'Serial Number',
                'key': 'serial_number',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., SN123456789',
                'help_text': 'Device serial number'
            },
            {
                'label': 'Brand',
                'key': 'brand',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., Apple, Samsung, LG',
                'help_text': 'Device brand'
            },
            {
                'label': 'Model',
                'key': 'model',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., iPhone 14, Galaxy S23',
                'help_text': 'Device model'
            },
            {
                'label': 'IMEI/MAC Address',
                'key': 'imei_mac',
                'type': 'text',
                'required': False,
                'placeholder': 'e.g., 123456789012345',
                'help_text': 'Unique device identifier'
            },
            {
                'label': 'Purchase Date',
                'key': 'purchase_date',
                'type': 'date',
                'required': False,
                'help_text': 'Date of purchase'
            },
            {
                'label': 'Warranty Expiry',
                'key': 'warranty_expiry',
                'type': 'date',
                'required': False,
                'help_text': 'Warranty expiration date'
            }
        ]
    },
    'machinery': {
        'name': 'Machinery & Equipment',
        'icon': 'bi-gear-wide-connected',
        'color': '#dc3545',
        'description': 'Industrial machinery, tools, and heavy equipment',
        'fields': [
            {
                'label': 'Equipment Type',
                'key': 'equipment_type',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., Forklift, Generator, Drill',
                'help_text': 'Type of machinery'
            },
            {
                'label': 'Serial Number',
                'key': 'serial_number',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., SN123456789',
                'help_text': 'Equipment serial number'
            },
            {
                'label': 'Manufacturer',
                'key': 'manufacturer',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., Caterpillar, Bosch',
                'help_text': 'Equipment manufacturer'
            },
            {
                'label': 'Model',
                'key': 'model',
                'type': 'text',
                'required': True,
                'placeholder': 'e.g., CAT 320D',
                'help_text': 'Equipment model'
            },
            {
                'label': 'Year of Manufacture',
                'key': 'manufacture_year',
                'type': 'number',
                'required': False,
                'placeholder': 'e.g., 2023',
                'help_text': 'Year manufactured'
            },
            {
                'label': 'Operating Hours',
                'key': 'operating_hours',
                'type': 'number',
                'required': False,
                'placeholder': 'e.g., 1500',
                'help_text': 'Total operating hours'
            },
            {
                'label': 'Last Maintenance',
                'key': 'last_maintenance',
                'type': 'date',
                'required': False,
                'help_text': 'Last maintenance date'
            },
            {
                'label': 'Next Maintenance',
                'key': 'next_maintenance',
                'type': 'date',
                'required': False,
                'help_text': 'Scheduled maintenance date'
            },
            {
                'label': 'Safety Certificate',
                'key': 'safety_certificate',
                'type': 'text',
                'required': False,
                'placeholder': 'Certificate number',
                'help_text': 'Safety certification number'
            }
        ]
    },
    'blank': {
        'name': 'Blank Category',
        'icon': 'bi-file-earmark',
        'color': '#6c757d',
        'description': 'Start from scratch with no pre-configured fields',
        'fields': []
    }
}


def get_template(template_key):
    """Get a specific template by key."""
    return CATEGORY_TEMPLATES.get(template_key)


def get_all_templates():
    """Get all available templates."""
    return CATEGORY_TEMPLATES


def get_template_list():
    """Get a list of templates with basic info (for UI display)."""
    return [
        {
            'key': key,
            'name': template['name'],
            'icon': template['icon'],
            'color': template['color'],
            'description': template['description'],
            'field_count': len(template['fields'])
        }
        for key, template in CATEGORY_TEMPLATES.items()
    ]
