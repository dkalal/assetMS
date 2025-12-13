import random
import pandas as pd
from faker import Faker

# Initialize Faker for generating realistic data
fake = Faker()

# Define possible categories for furniture attributes
statuses = ["active", "inactive", "maintenance"]
assigned_roles = ["manager", "staff", "intern"]
locations = ["HQ Office", "Branch A", "Branch B", "Warehouse"]
departments = ["HR", "Finance", "IT", "Operations", "Admin"]
materials = ["Wood", "Metal", "Plastic", "Glass", "Fabric"]

# Generate 100 fake furniture assets
furniture_data = []
for i in range(100):
    item = {
        "status": random.choice(statuses),
        "description": fake.sentence(nb_words=6),
        "assigned_to": random.choice(assigned_roles),
        "Name": fake.word().capitalize() + " " + random.choice(["Desk", "Chair", "Table", "Cabinet", "Shelf"]),
        "Location": random.choice(locations),
        "Purchase Date": fake.date_between(start_date="-5y", end_date="today"),
        "Department": random.choice(departments),
        "Material": random.choice(materials),
    }
    furniture_data.append(item)

# Convert into DataFrame
df_furniture = pd.DataFrame(furniture_data)

# Save to Excel for bulk import
output_file = "furniture_bulk_import_test.xlsx"
df_furniture.to_excel(output_file, index=False)

print(f"✅ Test data file created: {output_file}")
