from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from tenancy.models import Branch, Company, UserBranch
from users.models import User


class Command(BaseCommand):
    help = "Ensure each user has a primary branch within their company, with optional dry-run validation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform validation without writing changes.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        stats = defaultdict(int)
        messages: List[str] = []

        try:
            with transaction.atomic():
                users = (
                    User.objects.exclude(company__isnull=True)
                    .select_related("company")
                    .prefetch_related("user_branches__branch")
                )

                for user in users:
                    company: Company = user.company
                    branches = [membership for membership in user.user_branches.all() if membership.company_id == company.id]
                    primary_branches = [membership for membership in branches if membership.is_primary]

                    if not branches:
                        stats["missing_memberships"] += 1
                        messages.append(
                            f"User '{user}' has no branch memberships for company '{company}'."
                        )
                        continue

                    if len(primary_branches) == 1:
                        stats["already_compliant"] += 1
                        continue

                    if len(primary_branches) > 1:
                        # Demote all but the newest membership
                        latest = max(primary_branches, key=lambda membership: membership.updated_at)
                        demoted = 0
                        for membership in primary_branches:
                            if membership.pk == latest.pk:
                                continue
                            membership.is_primary = False
                            membership.save(update_fields=["is_primary", "updated_at"])
                            demoted += 1
                        stats["demoted_duplicates"] += demoted
                        stats["fixed_multi_primary"] += 1
                        continue

                    # No primary branch set: promote head office or first membership
                    preferred = next((m for m in branches if m.branch.is_head_office), None) or branches[0]
                    preferred.is_primary = True
                    preferred.save(update_fields=["is_primary", "updated_at"])
                    stats["promoted_primary"] += 1

                if dry_run:
                    self.stdout.write(self.style.WARNING("Dry-run mode enabled; rolling back changes."))
                    transaction.set_rollback(True)
        except Exception as exc:  # pragma: no cover - defensive
            raise BaseCommand.CommandError(f"Backfill failed: {exc}") from exc

        status_prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"{status_prefix}Users processed: {len(users)}"))
        for key, count in stats.items():
            self.stdout.write(self.style.SUCCESS(f"{status_prefix}{key.replace('_', ' ').title()}: {count}"))
        if messages:
            self.stdout.write(self.style.WARNING("Issues detected:"))
            for msg in messages:
                self.stdout.write(f" - {msg}")
