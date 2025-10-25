# Generated migration for adding description field to AssetCategory

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0015_add_filters_to_exportlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='assetcategory',
            name='description',
            field=models.TextField(blank=True, default='', help_text='Category description for better organization'),
        ),
    ]
