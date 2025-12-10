# Generated migration for self-service retirement workflow refactoring

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_add_user_retirement_fields'),
    ]

    operations = [
        # Update STATUS_CHOICES to include new workflow statuses
        migrations.AlterField(
            model_name='userretirement',
            name='status',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('requested', 'Requested'),
                    ('pending_approval', 'Pending Approval'),
                    ('approved', 'Approved'),
                    ('in_progress', 'In Progress'),
                    ('asset_handover', 'Asset Handover'),
                    ('final_review', 'Final Review'),
                    ('completed', 'Completed'),
                    ('rejected', 'Rejected'),
                    ('cancelled', 'Cancelled'),
                    # Keep old statuses for backward compatibility
                    ('pending_asset_transfer', 'Pending Asset Transfer'),
                    ('assets_transferred', 'Assets Transferred'),
                ],
                default='requested'
            ),
        ),
        
        # Add new fields for self-service workflow
        migrations.AddField(
            model_name='userretirement',
            name='effective_date',
            field=models.DateField(help_text='Desired last working day', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='reason_category',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('resignation', 'Resignation'),
                    ('retirement', 'Retirement'),
                    ('career_change', 'Career Change'),
                    ('relocation', 'Relocation'),
                    ('personal', 'Personal Reasons'),
                    ('termination', 'Termination'),
                    ('contract_end', 'Contract End'),
                    ('other', 'Other'),
                ],
                default='resignation'
            ),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='requested_by',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='submitted_retirement_requests',
                to=settings.AUTH_USER_MODEL,
                help_text='Person who submitted request (usually self)'
            ),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='request_date',
            field=models.DateTimeField(auto_now_add=True, help_text='When request was submitted', null=True),
        ),
        
        # Approval workflow fields
        migrations.AddField(
            model_name='userretirement',
            name='reviewed_by',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_retirements',
                to=settings.AUTH_USER_MODEL,
                help_text='Manager/Admin who reviewed request'
            ),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='reviewed_at',
            field=models.DateTimeField(null=True, blank=True, help_text='When request was reviewed'),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='approval_notes',
            field=models.TextField(blank=True, help_text='Comments from approver'),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='rejection_reason',
            field=models.TextField(blank=True, help_text='Reason for rejection if denied'),
        ),
        
        # Asset management fields
        migrations.AddField(
            model_name='userretirement',
            name='assets_returned',
            field=models.IntegerField(default=0, help_text='Number of assets returned'),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='assets_pending',
            field=models.IntegerField(default=0, help_text='Number of assets pending return'),
        ),
        
        # Processing fields
        migrations.AddField(
            model_name='userretirement',
            name='processed_by',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='processed_retirements',
                to=settings.AUTH_USER_MODEL,
                help_text='Admin processing retirement'
            ),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='processing_started_at',
            field=models.DateTimeField(null=True, blank=True, help_text='When processing started'),
        ),
        
        # Compliance checklist fields
        migrations.AddField(
            model_name='userretirement',
            name='exit_interview_completed',
            field=models.BooleanField(default=False, help_text='Exit interview conducted'),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='exit_interview_notes',
            field=models.TextField(blank=True, help_text='Exit interview notes'),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='access_revoked',
            field=models.BooleanField(default=False, help_text='System access revoked'),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='final_paycheck_processed',
            field=models.BooleanField(default=False, help_text='Final paycheck processed'),
        ),
        migrations.AddField(
            model_name='userretirement',
            name='benefits_terminated',
            field=models.BooleanField(default=False, help_text='Benefits terminated'),
        ),
        
        # Update existing fields help_text
        migrations.AlterField(
            model_name='userretirement',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='retirement_requests',
                to=settings.AUTH_USER_MODEL,
                help_text='Employee requesting retirement'
            ),
        ),
        migrations.AlterField(
            model_name='userretirement',
            name='retired_by',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='initiated_retirements',
                to=settings.AUTH_USER_MODEL,
                help_text='[DEPRECATED] Use requested_by instead'
            ),
        ),
        migrations.AlterField(
            model_name='userretirement',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, help_text='[DEPRECATED] Use request_date instead'),
        ),
        
        # Data migration: Populate new fields from old fields
        migrations.RunPython(
            code=lambda apps, schema_editor: migrate_existing_retirements(apps, schema_editor),
            reverse_code=migrations.RunPython.noop,
        ),
    ]


def migrate_existing_retirements(apps, schema_editor):
    """
    Migrate existing retirement records to new self-service model
    - Set requested_by = retired_by (admin initiated)
    - Set request_date = created_at
    - Map old statuses to new statuses
    - Set default effective_date
    """
    UserRetirement = apps.get_model('users', 'UserRetirement')
    from django.utils import timezone
    from datetime import timedelta
    
    for retirement in UserRetirement.objects.all():
        # Set requested_by (admin initiated for old records)
        if retirement.retired_by and not retirement.requested_by:
            retirement.requested_by = retirement.retired_by
        
        # Set request_date from created_at
        if not retirement.request_date:
            retirement.request_date = retirement.created_at
        
        # Set effective_date (use created_at + 30 days as default)
        if not retirement.effective_date and retirement.created_at:
            retirement.effective_date = (retirement.created_at + timedelta(days=30)).date()
        
        # Map old statuses to new statuses
        status_mapping = {
            'pending_asset_transfer': 'asset_handover',
            'assets_transferred': 'final_review',
            'completed': 'completed',
            'cancelled': 'cancelled',
        }
        
        if retirement.status in status_mapping:
            old_status = retirement.status
            retirement.status = status_mapping[old_status]
            
            # If completed, mark as approved and processed
            if retirement.status == 'completed':
                retirement.reviewed_by = retirement.retired_by
                retirement.reviewed_at = retirement.created_at
                retirement.processed_by = retirement.completed_by or retirement.retired_by
                retirement.processing_started_at = retirement.created_at
                retirement.access_revoked = True
        
        retirement.save(update_fields=[
            'requested_by', 'request_date', 'effective_date', 'status',
            'reviewed_by', 'reviewed_at', 'processed_by', 'processing_started_at',
            'access_revoked'
        ])
