# Generated migration for user branch transfer models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_user_email_verification_sent_at_and_more'),
        ('tenancy', '0011_alter_approvalrequest_request_type'),
        ('assets', '0024_remove_duplicatedetection_asset1_and_more'),
    ]

    operations = [
        # Create UserBranchTransferRequest table
        migrations.CreateModel(
            name='UserBranchTransferRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
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
                    max_length=50
                )),
                ('initiation_reason', models.TextField(help_text='Reason for initiating transfer (e.g., "Employee relocation")')),
                ('user_selection_notes', models.TextField(blank=True, help_text='Optional notes from user about their selections')),
                ('approval_reason', models.TextField(blank=True, help_text='Reason for approval decision')),
                ('rejection_reason', models.TextField(blank=True, help_text='Reason for rejection')),
                ('initiated_at', models.DateTimeField(auto_now_add=True, help_text='When transfer was initiated')),
                ('user_selection_at', models.DateTimeField(blank=True, help_text='When user submitted asset selections', null=True)),
                ('approval_decision_at', models.DateTimeField(blank=True, help_text='When admin/manager made approval decision', null=True)),
                ('completed_at', models.DateTimeField(blank=True, help_text='When transfer was fully executed', null=True)),
                ('total_assets', models.PositiveIntegerField(default=0, help_text='Total number of assets user had at initiation')),
                ('assets_selected_by_user', models.PositiveIntegerField(default=0, help_text='Number of assets user selected to transfer')),
                ('assets_approved', models.PositiveIntegerField(default=0, help_text='Number of assets approved by admin')),
                ('assets_transferred', models.PositiveIntegerField(default=0, help_text='Number of assets successfully transferred')),
                ('assets_unassigned', models.PositiveIntegerField(default=0, help_text='Number of assets successfully unassigned')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional metadata (e.g., HR ticket number, effective date)')),
                ('approved_by', models.ForeignKey(
                    blank=True,
                    help_text='Admin/Manager who approved transfer',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='approved_user_transfers',
                    to=settings.AUTH_USER_MODEL
                )),
                ('company', models.ForeignKey(
                    help_text='Company context for multi-tenancy',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='user_transfer_requests',
                    to='tenancy.company'
                )),
                ('from_branch', models.ForeignKey(
                    blank=True,
                    help_text='Original branch (can be null if user had no branch)',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='outgoing_user_transfers',
                    to='tenancy.branch'
                )),
                ('initiated_by', models.ForeignKey(
                    help_text='Admin/Manager who initiated transfer',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='initiated_user_transfers',
                    to=settings.AUTH_USER_MODEL
                )),
                ('to_branch', models.ForeignKey(
                    help_text='Destination branch',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='incoming_user_transfers',
                    to='tenancy.branch'
                )),
                ('user', models.ForeignKey(
                    help_text='User being transferred',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='transfer_requests',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'User Branch Transfer Request',
                'verbose_name_plural': 'User Branch Transfer Requests',
                'db_table': 'user_branch_transfer_requests',
                'ordering': ['-initiated_at'],
            },
        ),
        
        # Create AssetTransferSelection table
        migrations.CreateModel(
            name='AssetTransferSelection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('selected_by_user', models.BooleanField(default=False, help_text='Whether user selected this asset to transfer')),
                ('user_selection_reason', models.TextField(blank=True, help_text="User's reason for selecting this asset")),
                ('user_selected_at', models.DateTimeField(blank=True, help_text='When user selected/deselected this asset', null=True)),
                ('approved_by_admin', models.BooleanField(default=False, help_text='Whether admin approved this asset for transfer')),
                ('admin_decision_reason', models.TextField(blank=True, help_text="Admin's reason for approval/rejection")),
                ('admin_decision_at', models.DateTimeField(blank=True, help_text='When admin made approval decision', null=True)),
                ('status', models.CharField(
                    choices=[
                        ('not_selected', 'Not Selected (Will be returned)'),
                        ('selected', 'Selected by User'),
                        ('approved', 'Approved by Admin'),
                        ('rejected', 'Rejected by Admin'),
                        ('transferred', 'Successfully Transferred'),
                        ('unassigned', 'Successfully Unassigned'),
                    ],
                    db_index=True,
                    default='not_selected',
                    help_text='Current status of this selection',
                    max_length=50
                )),
                ('executed_at', models.DateTimeField(blank=True, help_text='When transfer/unassignment was executed', null=True)),
                ('execution_error', models.TextField(blank=True, help_text='Error message if execution failed')),
                ('asset_snapshot', models.JSONField(blank=True, default=dict, help_text='Snapshot of asset state at selection time')),
                ('asset', models.ForeignKey(
                    help_text='Asset being considered for transfer',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='transfer_selections',
                    to='assets.asset'
                )),
                ('company', models.ForeignKey(
                    help_text='Company context for multi-tenancy',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='asset_transfer_selections',
                    to='tenancy.company'
                )),
                ('transfer_request', models.ForeignKey(
                    help_text='Parent transfer request',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='asset_selections',
                    to='users.userbranchTransferrequest'
                )),
            ],
            options={
                'verbose_name': 'Asset Transfer Selection',
                'verbose_name_plural': 'Asset Transfer Selections',
                'db_table': 'asset_transfer_selections',
                'ordering': ['asset__category__name', 'asset__id'],
            },
        ),
        
        # Add indexes for UserBranchTransferRequest
        migrations.AddIndex(
            model_name='userbranchTransferrequest',
            index=models.Index(fields=['company', 'status'], name='user_branch_company_status_idx'),
        ),
        migrations.AddIndex(
            model_name='userbranchTransferrequest',
            index=models.Index(fields=['user', 'status'], name='user_branch_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='userbranchTransferrequest',
            index=models.Index(fields=['to_branch', 'status'], name='user_branch_to_branch_status_idx'),
        ),
        migrations.AddIndex(
            model_name='userbranchTransferrequest',
            index=models.Index(fields=['initiated_at'], name='user_branch_initiated_at_idx'),
        ),
        migrations.AddIndex(
            model_name='userbranchTransferrequest',
            index=models.Index(fields=['status', 'initiated_at'], name='user_branch_status_initiated_idx'),
        ),
        
        # Add indexes for AssetTransferSelection
        migrations.AddIndex(
            model_name='assettransferselection',
            index=models.Index(fields=['transfer_request', 'status'], name='asset_sel_request_status_idx'),
        ),
        migrations.AddIndex(
            model_name='assettransferselection',
            index=models.Index(fields=['transfer_request', 'selected_by_user'], name='asset_sel_request_selected_idx'),
        ),
        migrations.AddIndex(
            model_name='assettransferselection',
            index=models.Index(fields=['asset'], name='asset_sel_asset_idx'),
        ),
        migrations.AddIndex(
            model_name='assettransferselection',
            index=models.Index(fields=['company', 'status'], name='asset_sel_company_status_idx'),
        ),
        
        # Add unique constraint for AssetTransferSelection
        migrations.AddConstraint(
            model_name='assettransferselection',
            constraint=models.UniqueConstraint(
                fields=['transfer_request', 'asset'],
                name='unique_asset_per_transfer_request'
            ),
        ),
        
        # Add unique constraint for UserBranchTransferRequest (one active transfer per user)
        migrations.AddConstraint(
            model_name='userbranchTransferrequest',
            constraint=models.UniqueConstraint(
                fields=['user', 'company'],
                condition=models.Q(status__in=['pending_user_selection', 'pending_approval', 'approved']),
                name='unique_active_transfer_per_user'
            ),
        ),
    ]
