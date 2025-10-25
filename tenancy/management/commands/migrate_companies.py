from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tenancy.models import Branch, Company


class Command(BaseCommand):
    help = "Import companies and branches from a mapping file with optional dry-run validation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mapping",
            dest="mapping_path",
            required=True,
            help="Path to a JSON file defining companies and branches.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the mapping without committing changes.",
        )

    def handle(self, *args, **options):
        mapping_path = Path(options["mapping_path"])
        if not mapping_path.exists():
            raise CommandError(f"Mapping file not found: {mapping_path}")

        try:
            with mapping_path.open("r", encoding="utf-8") as fh:
                mapping = json.load(fh)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON mapping file: {exc}") from exc

        companies = mapping if isinstance(mapping, list) else mapping.get("companies")
        if not companies:
            raise CommandError("Mapping must define a non-empty 'companies' list.")

        normalized: List[Dict[str, Any]] = []
        for entry in companies:
            name = entry.get("name")
            if not name:
                raise CommandError("Each company entry must include a 'name'.")
            branches = entry.get("branches", [])
            if not isinstance(branches, list):
                raise CommandError(f"Company '{name}' branches must be a list.")
            normalized.append({"company": entry, "branches": branches})

        dry_run: bool = options["dry_run"]
        created_companies: List[Tuple[Company, bool]] = []
        created_branches: List[Tuple[Branch, bool]] = []

        try:
            with transaction.atomic():
                for entry in normalized:
                    company_payload = entry["company"]
                    company_defaults = {
                        key: company_payload[key]
                        for key in [
                            "address",
                            "tax_id",
                            "logo",
                            "contact_person",
                            "phone",
                            "email",
                            "timezone",
                            "metadata",
                        ]
                        if key in company_payload and company_payload[key] is not None
                    }
                    company, created = Company.objects.get_or_create(
                        name=company_payload["name"],
                        defaults=company_defaults,
                    )
                    created_companies.append((company, created))

                    if not created:
                        for attr, value in company_defaults.items():
                            if value is not None:
                                setattr(company, attr, value)
                        company.save(update_fields=list(company_defaults.keys()))

                    codes_seen = set()
                    for branch_payload in entry["branches"]:
                        branch_name = branch_payload.get("name")
                        branch_code = branch_payload.get("code")
                        if not branch_name or not branch_code:
                            raise CommandError(
                                f"Branches for company '{company.name}' must include 'name' and 'code'."
                            )
                        if branch_code in codes_seen:
                            raise CommandError(
                                f"Duplicate branch code '{branch_code}' for company '{company.name}'."
                            )
                        codes_seen.add(branch_code)
                        branch_defaults = {
                            key: branch_payload[key]
                            for key in ["address", "is_head_office", "metadata"]
                            if key in branch_payload and branch_payload[key] is not None
                        }
                        branch, branch_created = Branch.objects.update_or_create(
                            company=company,
                            code=branch_code,
                            defaults={
                                "name": branch_name,
                                **branch_defaults,
                            },
                        )
                        created_branches.append((branch, branch_created))

                if dry_run:
                    self.stdout.write(self.style.WARNING("Dry-run mode enabled; rolling back changes."))
                    transaction.set_rollback(True)
        except CommandError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise CommandError(f"Migration failed: {exc}") from exc

        created_company_count = sum(1 for _, created in created_companies if created)
        updated_company_count = len(created_companies) - created_company_count
        created_branch_count = sum(1 for _, created in created_branches if created)
        updated_branch_count = len(created_branches) - created_branch_count

        status_prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{status_prefix}Processed {len(created_companies)} companies "
                f"({created_company_count} created, {updated_company_count} updated)"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{status_prefix}Processed {len(created_branches)} branches "
                f"({created_branch_count} created, {updated_branch_count} updated)"
            )
        )
