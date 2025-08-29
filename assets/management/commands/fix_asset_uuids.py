from django.core.management.base import BaseCommand
from assets.models import Asset
import uuid
from collections import Counter

class Command(BaseCommand):
    help = 'Ensure all assets have unique, non-null UUIDs.'

    def handle(self, *args, **options):
        assets = Asset.objects.all()
        uuids = [str(a.uuid) for a in assets if a.uuid]
        uuid_counts = Counter(uuids)
        duplicates = {u for u, c in uuid_counts.items() if c > 1}
        fixed = 0
        for asset in assets:
            if not asset.uuid or str(asset.uuid) in duplicates:
                asset.uuid = uuid.uuid4()
                asset.save(update_fields=['uuid'])
                fixed += 1
        self.stdout.write(self.style.SUCCESS(f'Fixed {fixed} assets with missing or duplicate UUIDs.')) 