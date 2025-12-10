# Generated migration for user-initiated branch transfers

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_user_branch_transfer_models'),
    ]

    operations = [
        # Add initiation_type field
        migrations.AddField(
            model_name='userbranchTransferrequest',
            name='initiation_type',
            field=models.CharField(
                choices=[
                    ('admin_initiated', 'Admin Initiated'),
                    ('user_initiated', 'User Initiated'),
                ],
                default='admin_initiated',
                help_text='Who initiated this transfer request',
                max_length=20,
            ),
        ),
        
        # Add manager approval fields
        migrations.AddField(
            model_name='userbranchTransferrequest',
            name='manager_approved_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Manager who approved user-initiated transfer',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='manager_approved_user_transfers',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        
        migrations.AddField(
            model_name='userbranchTransferrequest',
            name='manager_approval_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When manager approved the request',
                null=True,
            ),
        ),
        
        migrations.AddField(
            model_name='userbranchTransferrequest',
            name='manager_approval_reason',
            field=models.TextField(
                blank=True,
                help_text='Manager approval/rejection reason',
            ),
        ),
        
        # Add new status for manager approval
        migrations.AlterField(
            model_name='userbranchTransferrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending_manager_approval', 'Pending Manager Approval'),
                    ('pending_user_selection', 'Pending User Selection'),
                    ('pending_approval', 'Pending Approval'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                ],
                db_index=True,
                default='pending_user_selection',
                help_text='Current workflow status',
                max_length=50,
            ),
        ),
        
        # Add index for initiation_type
        migrations.AddIndex(
            model_name='userbranchTransferrequest',
            index=models.Index(fields=['initiation_type', 'status'], name='user_transfer_init_status_idx'),
        ),
        
        # Add index for manager approval
        migrations.AddIndex(
            model_name='userbranchTransferrequest',
            index=models.Index(fields=['manager_approved_by', 'status'], name='user_transfer_mgr_status_idx'),
        ),
    ]
