from django.db import migrations, models


def assign_category_companies(apps, schema_editor):
    Asset = apps.get_model("assets", "Asset")
    AssetCategory = apps.get_model("assets", "AssetCategory")
    AssetCategoryField = apps.get_model("assets", "AssetCategoryField")
    Company = apps.get_model("tenancy", "Company")

    default_company = Company.objects.order_by("id").first()
    if default_company is None:
        default_company = Company.objects.create(name="Default Company (Auto)")

    for category in AssetCategory.objects.all():
        if category.company_id:
            AssetCategoryField.objects.filter(category_id=category.id, company_id__isnull=True).update(
                company_id=category.company_id
            )
            continue

        asset_company_ids = list(
            Asset.objects.filter(category_id=category.id)
            .exclude(company_id__isnull=True)
            .values_list("company_id", flat=True)
            .distinct()
        )

        if not asset_company_ids:
            category.company_id = default_company.id
            category.save(update_fields=["company"])
            AssetCategoryField.objects.filter(category_id=category.id).update(company_id=category.company_id)
            continue

        if len(asset_company_ids) == 1:
            company_id = asset_company_ids[0]
            category.company_id = company_id
            category.save(update_fields=["company"])
            AssetCategoryField.objects.filter(category_id=category.id).update(company_id=company_id)
            continue

        original_fields = list(AssetCategoryField.objects.filter(category_id=category.id))
        for company_id in asset_company_ids:
            new_category, created = AssetCategory.objects.get_or_create(
                name=category.name,
                company_id=company_id,
                defaults={"dynamic_fields": category.dynamic_fields},
            )
            if not created and new_category.dynamic_fields != category.dynamic_fields:
                new_category.dynamic_fields = category.dynamic_fields
                new_category.save(update_fields=["dynamic_fields"])

            Asset.objects.filter(category_id=category.id, company_id=company_id).update(category_id=new_category.id)

            existing_keys = set(
                AssetCategoryField.objects.filter(category_id=new_category.id).values_list("key", flat=True)
            )
            new_fields = []
            for field in original_fields:
                if field.key in existing_keys:
                    continue
                new_fields.append(
                    AssetCategoryField(
                        company_id=company_id,
                        category_id=new_category.id,
                        key=field.key,
                        label=field.label,
                        type=field.type,
                        required=field.required,
                    )
                )
            if new_fields:
                AssetCategoryField.objects.bulk_create(new_fields)

        AssetCategoryField.objects.filter(category_id=category.id).delete()
        if not Asset.objects.filter(category_id=category.id).exists():
            category.delete()


def noop(apps, schema_editor):
    """No-op reverse migration."""
    # Data rollback would require manual intervention; left intentionally empty.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0005_rename_tenancy_ale_recipi_c8d328_idx_tenancy_ale_recipie_654015_idx_and_more"),
        ("assets", "0011_assettransfer_approved_by_assettransfer_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="assetcategory",
            name="company",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.CASCADE,
                related_name="asset_categories",
                to="tenancy.company",
            ),
        ),
        migrations.AddField(
            model_name="assetcategoryfield",
            name="company",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.CASCADE,
                related_name="asset_category_fields",
                to="tenancy.company",
            ),
        ),
        migrations.RunPython(assign_category_companies, noop),
        migrations.AlterField(
            model_name="assetcategory",
            name="company",
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name="asset_categories",
                to="tenancy.company",
            ),
        ),
        migrations.AlterField(
            model_name="assetcategoryfield",
            name="company",
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name="asset_category_fields",
                to="tenancy.company",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="assetcategory",
            unique_together={("company", "name")},
        ),
        migrations.AddIndex(
            model_name="assetcategory",
            index=models.Index(fields=["company", "name"], name="asset_category_company_name"),
        ),
        migrations.AddIndex(
            model_name="assetcategoryfield",
            index=models.Index(fields=["company", "category"], name="asset_cat_field_company_cat"),
        ),
    ]
