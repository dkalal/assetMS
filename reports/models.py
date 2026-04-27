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

    @property
    def format(self) -> str:
        """Return the export format for this report.

        Priority order:
        1. Explicit metadata["format"] (preferred)
        2. File extension on the stored file
        3. Legacy usage where report_type stored formats ("pdf", "excel", "csv")

        This keeps existing rows working without requiring schema changes.
        """
        meta = self.metadata or {}
        fmt = str(meta.get("format") or "").lower()

        # Normalized explicit format
        if fmt in {"pdf", "csv"}:
            return fmt
        if fmt in {"excel", "xlsx"}:
            return "excel"

        # Infer from file extension when possible
        if self.file and getattr(self.file, "name", ""):
            name = self.file.name
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext in {"pdf", "csv"}:
                return ext
            if ext in {"xls", "xlsx"}:
                return "excel"

        # Legacy behaviour: report_type was used as the format
        if self.report_type in {"pdf", "excel", "csv"}:
            return self.report_type

        return ""

    @property
    def type_label(self) -> str:
        meta = self.metadata or {}
        token = str(meta.get("report_type") or "").lower()
        mapping = {
            "asset_summary": "Asset Summary",
            "maintenance": "Maintenance",
            "custom": "Custom",
            "individual": "Individual",
        }
        if token in mapping:
            return mapping[token]
        # Legacy fallback: some rows stored canonical type in report_type
        if self.report_type in mapping:
            return mapping[self.report_type]
        # Final fallback: show export format nicely
        fmt = self.format
        return fmt.title() if fmt else "Report"

    @property
    def subject_label(self) -> str:
        """Return the individual subject name for person-level reports."""
        meta = self.metadata or {}
        if str(meta.get("report_type") or "").lower() != "individual":
            return ""
        return str(meta.get("subject_user_name") or "").strip()
