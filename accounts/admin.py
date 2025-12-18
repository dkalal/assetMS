"""
Django Admin for Account Management
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import UserInvitation, CompanyRegistration, OnboardingProgress
from tenancy.admin_mixins import CompanyScopedAdmin


@admin.register(UserInvitation)
class UserInvitationAdmin(CompanyScopedAdmin):
    list_display = [
        'email', 'company', 'role', 'status_badge',
        'invited_by', 'sent_at', 'expires_at', 'actions_column'
    ]
    list_filter = ['status', 'role', 'company', 'sent_at']
    search_fields = ['email', 'first_name', 'last_name', 'company__name']
    readonly_fields = ['invitation_token', 'sent_at', 'accepted_at']
    
    fieldsets = (
        ('Invitation Details', {
            'fields': ('email', 'first_name', 'last_name', 'company', 'branch', 'role')
        }),
        ('Status', {
            'fields': ('status', 'invitation_token', 'sent_at', 'accepted_at', 'expires_at')
        }),
        ('Metadata', {
            'fields': ('invited_by',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'accepted': 'green',
            'expired': 'red',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def actions_column(self, obj):
        if obj.status == 'pending' and obj.is_valid():
            return format_html(
                '<a class="button" href="#">Resend</a> '
                '<a class="button" href="#">Cancel</a>'
            )
        return '-'
    actions_column.short_description = 'Actions'


@admin.register(CompanyRegistration)
class CompanyRegistrationAdmin(CompanyScopedAdmin):
    list_display = [
        'company', 'plan_badge', 'subscription_status_badge',
        'trial_info', 'created_at'
    ]
    list_filter = ['plan', 'subscription_status', 'created_at']
    search_fields = ['company__name', 'billing_email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Company', {
            'fields': ('company', 'billing_email')
        }),
        ('Subscription', {
            'fields': ('plan', 'subscription_status', 'trial_ends_at')
        }),
        ('Resource Limits', {
            'fields': ('max_users', 'max_assets', 'max_storage_mb'),
            'classes': ('collapse',)
        }),
        ('Payment Integration', {
            'fields': ('payment_provider', 'payment_customer_id', 'payment_subscription_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def plan_badge(self, obj):
        colors = {
            'free': '#6c757d',
            'pro': '#007bff',
            'enterprise': '#28a745',
        }
        color = colors.get(obj.plan, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_plan_display()
        )
    plan_badge.short_description = 'Plan'
    
    def subscription_status_badge(self, obj):
        colors = {
            'trial': 'orange',
            'active': 'green',
            'past_due': 'red',
            'cancelled': 'gray',
            'suspended': 'darkred',
        }
        color = colors.get(obj.subscription_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_subscription_status_display()
        )
    subscription_status_badge.short_description = 'Status'
    
    def trial_info(self, obj):
        if obj.subscription_status == 'trial' and obj.trial_ends_at:
            days_left = obj.days_until_trial_ends()
            if days_left is not None:
                if days_left > 0:
                    return format_html(
                        '<span style="color: orange;">{} days left</span>',
                        days_left
                    )
                else:
                    return format_html('<span style="color: red;">Expired</span>')
        return '-'
    trial_info.short_description = 'Trial'


@admin.register(OnboardingProgress)
class OnboardingProgressAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'completion_bar', 'current_step',
        'company_details_completed', 'team_invited', 'tour_completed',
        'completed_at'
    ]
    list_filter = ['skipped', 'completed_at', 'current_step']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'completion_percentage']
    
    fieldsets = (
        ('User', {
            'fields': ('user', 'current_step')
        }),
        ('Progress', {
            'fields': (
                'company_details_completed',
                'team_invited',
                'tour_completed',
                'first_asset_created',
            )
        }),
        ('Status', {
            'fields': ('skipped', 'completed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def completion_bar(self, obj):
        percentage = obj.completion_percentage
        color = 'green' if percentage == 100 else 'orange' if percentage >= 50 else 'red'
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; padding: 2px 5px; border-radius: 3px; color: white; font-size: 11px; text-align: center;">'
            '{}%'
            '</div></div>',
            percentage, color, percentage
        )
    completion_bar.short_description = 'Progress'
