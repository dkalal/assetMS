# Generated migration for Intelligent Duplicate Detection System
# World-class implementation following Django best practices
# Author: World-Class Software Engineer
# Date: 2025-01-13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0020_add_unique_field_flag'),
        ('tenancy', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ========================================
        # 1. Duplicate Detection Rule Model
        # ========================================
        migrations.CreateModel(
            name='DuplicateDetectionRule',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False
                )),
                ('name', models.CharField(
                    max_length=100,
                    help_text='Rule name for identification'
                )),
                ('description', models.TextField(
                    blank=True,
                    help_text='Detailed description of what this rule detects'
                )),
                ('rule_type', models.CharField(
                    max_length=20,
                    choices=[
                        ('exact', 'Exact Match'),
                        ('fuzzy', 'Fuzzy Match'),
                        ('composite', 'Composite Key'),
                        ('pattern', 'Pattern Recognition'),
                        ('ml_based', 'Machine Learning')
                    ],
                    default='fuzzy'
                )),
                ('algorithm', models.CharField(
                    max_length=20,
                    choices=[
                        ('exact', 'Exact Comparison'),
                        ('levenshtein', 'Levenshtein Distance'),
                        ('jaro_winkler', 'Jaro-Winkler'),
                        ('soundex', 'Soundex Phonetic'),
                        ('metaphone', 'Metaphone Phonetic'),
                        ('trigram', 'Trigram Similarity'),
                        ('cosine', 'Cosine Similarity')
                    ],
                    default='levenshtein'
                )),
                ('fields', models.JSONField(
                    default=list,
                    help_text='List of fields to check'
                )),
                ('weights', models.JSONField(
                    default=dict,
                    help_text='Field weights for scoring'
                )),
                ('options', models.JSONField(
                    default=dict,
                    help_text='Additional rule options'
                )),
                ('threshold', models.IntegerField(
                    default=90,
                    help_text='Confidence threshold to flag as duplicate (0-100)'
                )),
                ('auto_flag_threshold', models.IntegerField(
                    default=95,
                    help_text='Threshold for automatic flagging'
                )),
                ('priority', models.IntegerField(
                    default=1,
                    help_text='Rule priority (higher = more important)'
                )),
                ('active', models.BooleanField(
                    default=True,
                    help_text='Whether this rule is currently active'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='duplicate_rules',
                    to='tenancy.company'
                )),
                ('category', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to='assets.assetcategory',
                    help_text='Apply to specific category or all if null'
                )),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_duplicate_rules',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'ordering': ['-priority', 'name'],
            },
        ),
        
        # ========================================
        # 2. Duplicate Scan History Model
        # ========================================
        migrations.CreateModel(
            name='DuplicateScanHistory',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False
                )),
                ('scan_type', models.CharField(
                    max_length=50,
                    choices=[
                        ('manual', 'Manual Scan'),
                        ('scheduled', 'Scheduled Scan'),
                        ('import', 'Import Scan'),
                        ('api', 'API Triggered')
                    ],
                    default='manual'
                )),
                ('total_assets_scanned', models.IntegerField(default=0)),
                ('duplicates_found', models.IntegerField(default=0)),
                ('exact_matches', models.IntegerField(default=0)),
                ('likely_duplicates', models.IntegerField(default=0)),
                ('possible_duplicates', models.IntegerField(default=0)),
                ('scan_duration', models.FloatField(
                    help_text='Scan duration in seconds'
                )),
                ('configuration', models.JSONField(
                    default=dict,
                    help_text='Scan configuration and parameters'
                )),
                ('started_at', models.DateTimeField()),
                ('completed_at', models.DateTimeField()),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='duplicate_scans',
                    to='tenancy.company'
                )),
                ('branch', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='tenancy.branch',
                    help_text='Branch scanned, or null for all'
                )),
                ('category', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='assets.assetcategory',
                    help_text='Category scanned, or null for all'
                )),
                ('initiated_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='initiated_duplicate_scans',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
        
        # ========================================
        # 3. Duplicate Detection Model
        # ========================================
        migrations.CreateModel(
            name='DuplicateDetection',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False
                )),
                ('confidence_score', models.IntegerField(
                    help_text='Confidence score (0-100)'
                )),
                ('detection_method', models.CharField(
                    max_length=50,
                    help_text='Method used for detection'
                )),
                ('matched_fields', models.JSONField(
                    default=dict,
                    help_text='Fields that matched and their scores'
                )),
                ('status', models.CharField(
                    max_length=20,
                    choices=[
                        ('pending', 'Pending Review'),
                        ('confirmed', 'Confirmed Duplicate'),
                        ('resolved', 'Resolved'),
                        ('ignored', 'Ignored - Not Duplicate'),
                        ('investigating', 'Under Investigation')
                    ],
                    default='pending'
                )),
                ('resolution_action', models.CharField(
                    max_length=20,
                    blank=True,
                    null=True,
                    choices=[
                        ('merged', 'Assets Merged'),
                        ('linked', 'Assets Linked'),
                        ('not_duplicate', 'Marked as Not Duplicate'),
                        ('deleted', 'Duplicate Deleted'),
                        ('no_action', 'No Action Taken')
                    ]
                )),
                ('resolution_notes', models.TextField(
                    blank=True,
                    help_text='Notes about the resolution'
                )),
                ('detected_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('last_reviewed', models.DateTimeField(blank=True, null=True)),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='duplicate_detections',
                    to='tenancy.company'
                )),
                ('asset1', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='duplicate_detections_as_primary',
                    to='assets.asset'
                )),
                ('asset2', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='duplicate_detections_as_duplicate',
                    to='assets.asset'
                )),
                ('detected_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='detected_duplicates',
                    to=settings.AUTH_USER_MODEL,
                    help_text='User or system that detected'
                )),
                ('resolved_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='resolved_duplicates',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'ordering': ['-confidence_score', '-detected_at'],
            },
        ),
        
        # ========================================
        # 4. Asset Merge History Model
        # ========================================
        migrations.CreateModel(
            name='AssetMergeHistory',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False
                )),
                ('merged_asset_id', models.CharField(
                    max_length=50,
                    help_text='ID of asset that was merged (preserved even if deleted)'
                )),
                ('merged_asset_data', models.JSONField(
                    help_text='Complete data of merged asset for audit'
                )),
                ('fields_updated', models.JSONField(
                    default=dict,
                    help_text='Fields that were updated in primary asset'
                )),
                ('conflicts_resolved', models.JSONField(
                    default=dict,
                    help_text='Field conflicts and how they were resolved'
                )),
                ('merge_reason', models.TextField(
                    blank=True,
                    help_text='Reason for merge'
                )),
                ('relationships_transferred', models.JSONField(
                    default=dict,
                    help_text='Count of relationships transferred'
                )),
                ('merged_at', models.DateTimeField(auto_now_add=True)),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='asset_merges',
                    to='tenancy.company'
                )),
                ('primary_asset', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='merges_as_primary',
                    to='assets.asset',
                    help_text='Asset that was kept'
                )),
                ('detection', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='assets.duplicatedetection'
                )),
                ('merged_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='performed_merges',
                    to=settings.AUTH_USER_MODEL
                )),
                ('approved_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='approved_merges',
                    to=settings.AUTH_USER_MODEL,
                    help_text='Supervisor approval if required'
                )),
            ],
            options={
                'ordering': ['-merged_at'],
            },
        ),
        
        # ========================================
        # 5. Many-to-Many Relationships
        # ========================================
        migrations.AddField(
            model_name='duplicatescanhistory',
            name='rules_applied',
            field=models.ManyToManyField(
                help_text='Rules used in this scan',
                to='assets.duplicatedetectionrule'
            ),
        ),
        migrations.AddField(
            model_name='duplicatedetection',
            name='rules_triggered',
            field=models.ManyToManyField(
                blank=True,
                help_text='Rules that flagged this duplicate',
                to='assets.duplicatedetectionrule'
            ),
        ),
        
        # ========================================
        # 6. Database Indexes for Performance
        # ========================================
        migrations.AddIndex(
            model_name='duplicatedetectionrule',
            index=models.Index(
                fields=['company', 'active'],
                name='assets_dupl_company_active_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='duplicatedetectionrule',
            index=models.Index(
                fields=['category', 'active'],
                name='assets_dupl_category_active_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='duplicatescanhistory',
            index=models.Index(
                fields=['company', '-started_at'],
                name='assets_dupl_company_scan_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='duplicatedetection',
            index=models.Index(
                fields=['company', 'status'],
                name='assets_dupl_company_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='duplicatedetection',
            index=models.Index(
                fields=['confidence_score'],
                name='assets_dupl_confidence_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='duplicatedetection',
            index=models.Index(
                fields=['-detected_at'],
                name='assets_dupl_detected_at_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='assetmergehistory',
            index=models.Index(
                fields=['company', '-merged_at'],
                name='assets_merge_company_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='assetmergehistory',
            index=models.Index(
                fields=['primary_asset'],
                name='assets_merge_primary_idx'
            ),
        ),
        
        # ========================================
        # 7. Unique Constraints
        # ========================================
        migrations.AlterUniqueTogether(
            name='duplicatedetectionrule',
            unique_together={('company', 'name')},
        ),
    ]
