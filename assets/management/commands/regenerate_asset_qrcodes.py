from django.core.management.base import BaseCommand
from assets.models import Asset
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Regenerate QR codes for all assets using the direct URL format.'

    def handle(self, *args, **options):
        updated = 0
        # You may need to set your base URL here if not running in a request context
        base_url = 'https://yourdomain.com'  # TODO: Set your actual domain here
        for asset in Asset.objects.all():
            qr_url = f"{base_url}/assets/{asset.uuid}/"
            qr = qrcode.make(qr_url)
            buffer = BytesIO()
            qr.save(buffer, 'PNG')
            asset.qr_code.save(f"asset_{asset.uuid}.png", ContentFile(buffer.getvalue()), save=False)
            asset.save()
            updated += 1
        self.stdout.write(self.style.SUCCESS(f'Regenerated QR codes for {updated} assets.')) 