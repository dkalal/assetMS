from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_remove_assettransferselection_unique_asset_per_transfer_request_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='can_manage_customers',
            field=models.BooleanField(
                default=False,
                help_text='Can view customers, link/unlink assets, and add notes (branch-scoped).',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='can_transfer_assets',
            field=models.BooleanField(
                default=False,
                help_text='Can initiate asset transfers (branch-to-branch and customer-to-customer).',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='can_schedule_maintenance',
            field=models.BooleanField(
                default=False,
                help_text='Can schedule and manage maintenance for assets of assigned customers.',
            ),
        ),
    ]
