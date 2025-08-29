from django.db import models
from django.conf import settings

class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ]
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='reports/')

    def __str__(self):
        return f"{self.report_type} report by {self.created_by} at {self.created_at}"
