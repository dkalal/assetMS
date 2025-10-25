from django.conf import settings
from django.db import models


class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ("pdf", "PDF"),
        ("excel", "Excel"),
        ("csv", "CSV"),
    ]

    company = models.ForeignKey(
        "tenancy.Company",
        on_delete=models.CASCADE,
        related_name="reports",
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "tenancy.Branch",
        on_delete=models.SET_NULL,
        related_name="reports",
        null=True,
        blank=True,
    )
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="reports/", blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "branch", "created_at"], name="report_company_branch_ts"),
            models.Index(fields=["report_type", "created_at"], name="report_type_ts"),
        ]

    def __str__(self):
        company_label = f" @ {self.company.name}" if self.company else ""
        return f"{self.get_report_type_display()} report{company_label} on {self.created_at:%Y-%m-%d %H:%M}"
