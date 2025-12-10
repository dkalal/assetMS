from django.apps import AppConfig


class AssetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'assets'
    
    def ready(self):
        """
        Import signals when app is ready
        This ensures signals are connected when Django starts
        """
        import assets.signals  # noqa: F401
