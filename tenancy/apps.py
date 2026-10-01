from django.apps import AppConfig


class TenancyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tenancy"
    verbose_name = "Multi-Tenancy"

    def ready(self):
        from tenancy import checks  # noqa: F401
