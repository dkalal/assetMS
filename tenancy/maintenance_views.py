"""Views enabling RBAC controlled maintenance management from the tenant portal."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.db.models import Q

from assets.forms import (
    MaintenanceCancellationForm,
    MaintenanceCompletionForm,
    MaintenanceScheduleForm,
    MaintenanceStartForm,
)
from assets.models import Asset, MaintenanceRecord
from assets.services.maintenance import MaintenanceService
from tenancy.mixins import BranchContextMixin


class MaintenanceRBACMixin(LoginRequiredMixin, BranchContextMixin):
    allowed_roles = {"manager", "admin"}

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if getattr(request.user, "role", None) not in self.allowed_roles and not request.user.is_superuser:
            messages.error(request, "You do not have permission to access maintenance management.")
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


class MaintenanceListView(MaintenanceRBACMixin, TemplateView):
    template_name = "maintenance/maintenance_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "company", None)
        branch = getattr(self.request, "branch", None)
        user = self.request.user

        branch_ids: list[int] | None
        if branch:
            branch_ids = [branch.id]
        elif user.is_superuser or getattr(user, "role", None) == "admin":
            branch_ids = None
        else:
            memberships = getattr(self.request, "available_branches", [])
            branch_ids = [membership.branch_id for membership in memberships if membership.branch_id]
            if not branch_ids:
                branch_ids = []

        # Filter maintenance records by company and active assets only
        # Excludes records for retired, disposed, or lost assets
        records = (
            MaintenanceRecord.objects.filter(
                company=company,
                asset__status__in=['active', 'in_maintenance']  # Only active and in-maintenance assets
            )
            .select_related(
                "asset",
                "asset__branch",
                "asset__category",
                "performed_by",
                "supervisor",
            )
        )
        if branch_ids is not None:
            if branch_ids:
                records = records.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
            else:
                records = records.none()

        # Filter eligible assets - only ACTIVE assets with maintenance enabled
        # Excludes assets that are: retired, disposed, lost, or CURRENTLY IN MAINTENANCE
        # World-class logic: Assets under maintenance cannot be scheduled for NEW maintenance
        assets_qs = (
            Asset.objects.filter(
                company=company,
                maintenance_enabled=True,
                status='active'  # Only ACTIVE assets (exclude in_maintenance)
            )
            .select_related("branch", "category")
        )
        if branch_ids is not None:
            if branch_ids:
                assets_qs = assets_qs.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
            else:
                assets_qs = assets_qs.none()

        today = timezone.localdate()
        upcoming_qs = records.filter(
            status=MaintenanceRecord.Status.SCHEDULED,
            scheduled_for__gte=today,
        ).order_by("scheduled_for")
        overdue_qs = records.filter(
            status=MaintenanceRecord.Status.SCHEDULED,
            scheduled_for__lt=today,
        ).order_by("scheduled_for")
        # WORLD-CLASS: Add IN_PROGRESS section for active maintenance work
        in_progress_qs = records.filter(
            status=MaintenanceRecord.Status.IN_PROGRESS,
        ).order_by("started_at")
        recent_qs = records.filter(
            status=MaintenanceRecord.Status.COMPLETED,
            completed_at__gte=timezone.now() - timedelta(days=30),
        ).order_by("-completed_at")

        upcoming_records = list(upcoming_qs)
        overdue_records = list(overdue_qs)
        in_progress_records = list(in_progress_qs)
        recent_records = list(recent_qs)
        eligible_assets = list(assets_qs)

        context.update(
            {
                "upcoming_records": upcoming_records,
                "overdue_records": overdue_records,
                "in_progress_records": in_progress_records,
                "recent_records": recent_records,
                "assets": eligible_assets,
                "stats": {
                    "eligible_assets": len(eligible_assets),
                    "upcoming": len(upcoming_records),
                    "overdue": len(overdue_records),
                    "in_progress": len(in_progress_records),
                    "recent": len(recent_records),
                },
                "today": today,
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class MaintenanceScheduleView(MaintenanceRBACMixin, View):
    template_name = "maintenance/maintenance_form.html"

    def get(self, request: HttpRequest, asset_uuid: str) -> HttpResponse:
        asset = get_object_or_404(
            Asset.objects.filter(uuid=asset_uuid, company=request.company).select_related("branch"),
            Q(branch=request.branch)
            | Q(branch__isnull=True)
            | (
                Q(branch__in=[membership.branch for membership in getattr(request, "available_branches", [])])
                if not (request.user.is_superuser or getattr(request.user, "role", None) == "admin")
                else Q()
            ),
        )
        form = MaintenanceScheduleForm(request=request, asset=asset)
        return render(request, self.template_name, {"form": form, "asset": asset, "action": "schedule"})

    def post(self, request: HttpRequest, asset_uuid: str) -> HttpResponse:
        asset = get_object_or_404(
            Asset.objects.filter(uuid=asset_uuid, company=request.company).select_related("branch"),
            Q(branch=request.branch)
            | Q(branch__isnull=True)
            | (
                Q(branch__in=[membership.branch for membership in getattr(request, "available_branches", [])])
                if not (request.user.is_superuser or getattr(request.user, "role", None) == "admin")
                else Q()
            ),
        )
        form = MaintenanceScheduleForm(request.POST, request=request, asset=asset)
        if form.is_valid():
            MaintenanceService.schedule(
                asset=asset,
                scheduled_for=form.cleaned_data["scheduled_for"],
                created_by=request.user,
                supervisor=form.cleaned_data.get("supervisor"),
                description=form.cleaned_data.get("description", ""),
            )
            messages.success(request, "Maintenance scheduled successfully.")
            return redirect(reverse("maintenance:list"))
        return render(request, self.template_name, {"form": form, "asset": asset, "action": "schedule"})


@method_decorator(login_required, name="dispatch")
class MaintenanceStartView(MaintenanceRBACMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        record = get_object_or_404(MaintenanceRecord, pk=pk, company=request.company)
        form = MaintenanceStartForm(request.POST, request=request, record=record)
        if form.is_valid():
            MaintenanceService.start(record=record, started_by=request.user)
            messages.success(request, "Maintenance marked as started.")
        else:
            messages.error(request, "; ".join(sum(form.errors.values(), [])))
        return redirect(reverse("maintenance:list"))


@method_decorator(login_required, name="dispatch")
class MaintenanceCompletionView(MaintenanceRBACMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        record = get_object_or_404(MaintenanceRecord, pk=pk, company=request.company)
        form = MaintenanceCompletionForm(request.POST, request=request, record=record)
        if form.is_valid():
            MaintenanceService.complete(
                record=record,
                completed_by=request.user,
                outcome_notes=form.cleaned_data.get("outcome_notes", ""),
                cost=form.cleaned_data.get("cost"),
            )
            messages.success(request, "Maintenance marked as completed.")
        else:
            messages.error(request, "; ".join(sum(form.errors.values(), [])))
        return redirect(reverse("maintenance:list"))


@method_decorator(login_required, name="dispatch")
class MaintenanceCancellationView(MaintenanceRBACMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        record = get_object_or_404(MaintenanceRecord, pk=pk, company=request.company)
        form = MaintenanceCancellationForm(request.POST, request=request, record=record)
        if form.is_valid():
            MaintenanceService.cancel(
                record=record,
                cancelled_by=request.user,
                reason=form.cleaned_data.get("reason", ""),
            )
            messages.info(request, "Maintenance record cancelled.")
        else:
            messages.error(request, "; ".join(sum(form.errors.values(), [])))
        return redirect(reverse("maintenance:list"))


@require_POST
@csrf_protect
@login_required
def seed_maintenance_data(request: HttpRequest) -> JsonResponse:
    """
    Generate sample maintenance data for testing and demonstration.
    Admin only. Creates maintenance-enabled assets and sample records.
    """
    # Security: Admin only
    if getattr(request.user, "role", None) != "admin" and not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "Admin access required"}, status=403)

    company = getattr(request, "company", None)
    if not company:
        return JsonResponse({"success": False, "error": "No company context"}, status=400)

    try:
        # Configuration
        num_assets = 10
        num_records = 15
        
        # Get active assets
        assets = list(Asset.objects.filter(
            company=company,
            status='active'
        ).select_related('branch', 'category')[:num_assets])

        if not assets:
            return JsonResponse({
                "success": False,
                "error": "No active assets found. Please create some assets first."
            }, status=400)

        # Enable maintenance for assets
        Asset.objects.filter(id__in=[a.id for a in assets]).update(maintenance_enabled=True)

        # Sample data
        descriptions = [
            "Routine preventive maintenance",
            "Quarterly inspection and service",
            "Annual comprehensive check",
            "Software update and optimization",
            "Hardware component replacement",
            "Calibration and testing",
            "Safety inspection",
            "Performance optimization",
            "Firmware upgrade",
            "Cleaning and lubrication",
        ]

        outcome_notes = [
            "All systems functioning normally. No issues detected.",
            "Minor adjustments made. Equipment running optimally.",
            "Replaced worn components. Performance improved significantly.",
            "Software updated successfully. All tests passed.",
            "Routine maintenance completed as scheduled.",
            "Calibration completed within acceptable tolerances.",
            "Safety checks passed. Equipment certified for continued use.",
            "Performance benchmarks exceeded expectations.",
            "Preventive measures applied. Next service scheduled.",
            "Comprehensive inspection completed. Asset in excellent condition.",
        ]

        today = timezone.localdate()
        records_created = 0

        # Distribution: 30% overdue, 40% upcoming, 20% completed, 10% in progress
        overdue_count = int(num_records * 0.3)
        upcoming_count = int(num_records * 0.4)
        completed_count = int(num_records * 0.2)
        in_progress_count = num_records - overdue_count - upcoming_count - completed_count

        # Create overdue records
        for i in range(overdue_count):
            asset = random.choice(assets)
            days_overdue = random.randint(1, 30)
            scheduled_date = today - timedelta(days=days_overdue)
            
            MaintenanceRecord.objects.create(
                asset=asset,
                company=company,
                branch=asset.branch,
                status=MaintenanceRecord.Status.SCHEDULED,
                scheduled_for=scheduled_date,
                description=random.choice(descriptions),
                created_by=request.user,
                updated_by=request.user,
            )
            records_created += 1

        # Create upcoming records
        for i in range(upcoming_count):
            asset = random.choice(assets)
            days_ahead = random.randint(1, 30)
            scheduled_date = today + timedelta(days=days_ahead)
            
            MaintenanceRecord.objects.create(
                asset=asset,
                company=company,
                branch=asset.branch,
                status=MaintenanceRecord.Status.SCHEDULED,
                scheduled_for=scheduled_date,
                description=random.choice(descriptions),
                supervisor=request.user if random.random() > 0.5 else None,
                created_by=request.user,
                updated_by=request.user,
            )
            records_created += 1

        # Create completed records
        for i in range(completed_count):
            asset = random.choice(assets)
            days_ago = random.randint(1, 30)
            scheduled_date = today - timedelta(days=days_ago + 5)
            completed_date = timezone.now() - timedelta(days=days_ago)
            started_date = completed_date - timedelta(hours=random.randint(1, 8))
            
            MaintenanceRecord.objects.create(
                asset=asset,
                company=company,
                branch=asset.branch,
                status=MaintenanceRecord.Status.COMPLETED,
                scheduled_for=scheduled_date,
                started_at=started_date,
                completed_at=completed_date,
                description=random.choice(descriptions),
                outcome_notes=random.choice(outcome_notes),
                cost=Decimal(str(random.uniform(50, 500))).quantize(Decimal('0.01')),
                performed_by=request.user,
                supervisor=request.user if random.random() > 0.5 else None,
                created_by=request.user,
                updated_by=request.user,
            )
            records_created += 1

        # Create in-progress records
        for i in range(in_progress_count):
            asset = random.choice(assets)
            scheduled_date = today - timedelta(days=random.randint(0, 3))
            started_date = timezone.now() - timedelta(hours=random.randint(1, 24))
            
            MaintenanceRecord.objects.create(
                asset=asset,
                company=company,
                branch=asset.branch,
                status=MaintenanceRecord.Status.IN_PROGRESS,
                scheduled_for=scheduled_date,
                started_at=started_date,
                description=random.choice(descriptions),
                performed_by=request.user,
                supervisor=request.user if random.random() > 0.5 else None,
                created_by=request.user,
                updated_by=request.user,
            )
            records_created += 1

        return JsonResponse({
            "success": True,
            "message": f"Successfully created {records_created} maintenance records for {len(assets)} assets!",
            "stats": {
                "assets_enabled": len(assets),
                "records_created": records_created,
                "overdue": overdue_count,
                "upcoming": upcoming_count,
                "completed": completed_count,
                "in_progress": in_progress_count,
            }
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Failed to generate sample data: {str(e)}"
        }, status=500)
