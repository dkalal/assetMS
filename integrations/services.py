from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from urllib import error, request
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from audit.utils import log_audit

from .models import CustomerSyncRun, ExternalCustomerReference, ExternalCustomerSyncConfig


logger = logging.getLogger(__name__)


class SourceCustomerApiError(Exception):
    pass


class SourceCustomerApiAuthError(SourceCustomerApiError):
    pass


def get_sync_timeout_seconds() -> int:
    return int(getattr(settings, 'EXTERNAL_CUSTOMER_SYNC_TIMEOUT_SECONDS', 15))


def normalize_source_base_url(raw_url: str) -> str:
    """
    Normalize the configured source URL to a host root.

    The integration UI stores a "base URL" rather than a full endpoint.
    If an operator pastes a UI path such as `/customers`, we strip that path
    so the sync client always appends the API route to the real origin.
    """
    value = (raw_url or '').strip()
    if not value:
        return ''

    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return value.rstrip('/')

    return urlunsplit((parsed.scheme, parsed.netloc, '', '', ''))


@dataclass
class SyncOutcome:
    run: CustomerSyncRun
    created: int
    updated: int
    skipped: int
    failed: int
    status: str
    error_summary: str


class SourceCustomerApiClient:
    def __init__(self, *, base_url: str, api_token: str, timeout: int | None = None):
        self.base_url = normalize_source_base_url(base_url).rstrip('/')
        self.api_token = api_token
        self.timeout = timeout or get_sync_timeout_seconds()

    def fetch_customer_pages(self):
        next_url = f'{self.base_url}/api/integrations/customers/'
        while next_url:
            payload = self._get_json(next_url)
            if not isinstance(payload, dict):
                raise SourceCustomerApiError('Unexpected customer list payload.')
            results = payload.get('results')
            if not isinstance(results, list):
                raise SourceCustomerApiError('Customer list payload missing results.')
            yield results
            next_url = payload.get('next')

    def _get_json(self, url: str):
        req = request.Request(
            url,
            headers={
                'Authorization': f'Token {self.api_token}',
                'Accept': 'application/json',
            },
            method='GET',
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise SourceCustomerApiAuthError(f'Source API authentication failed with status {exc.code}.') from exc
            raise SourceCustomerApiError(f'Source API request failed with status {exc.code}.') from exc
        except error.URLError as exc:
            raise SourceCustomerApiError(f'Source API connection failed: {exc.reason}') from exc
        except TimeoutError as exc:
            raise SourceCustomerApiError('Source API request timed out.') from exc
        except json.JSONDecodeError as exc:
            raise SourceCustomerApiError('Source API returned invalid JSON.') from exc


class CustomerSyncService:
    SYNC_FIELDS = (
        'full_name',
        'phone',
        'email',
        'address',
        'customer_status',
        'customer_type',
        'source_created_at',
    )

    @classmethod
    def sync_company_customers(cls, *, company, initiated_by):
        config = ExternalCustomerSyncConfig.objects.filter(company=company, is_enabled=True).first()
        if config is None:
            raise SourceCustomerApiError('Customer sync is not configured for this company.')

        sync_run = CustomerSyncRun.objects.create(company=company, initiated_by=initiated_by)
        client = SourceCustomerApiClient(
            base_url=config.source_base_url,
            api_token=config.api_token,
        )

        created = updated = skipped = failed = 0
        errors = []

        try:
            for page in client.fetch_customer_pages():
                for row in page:
                    try:
                        result = cls._upsert_reference(company=company, payload=row)
                    except Exception as exc:  # pragma: no cover - safety net for per-record failures
                        failed += 1
                        errors.append(str(exc))
                        logger.exception('Customer sync record failed for company=%s', company.id)
                        continue

                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
                    else:
                        skipped += 1
        except SourceCustomerApiAuthError as exc:
            status = CustomerSyncRun.Status.PARTIAL if (created or updated or skipped or failed) else CustomerSyncRun.Status.FAILED
            errors.append(str(exc))
        except SourceCustomerApiError as exc:
            status = CustomerSyncRun.Status.PARTIAL if (created or updated or skipped or failed) else CustomerSyncRun.Status.FAILED
            errors.append(str(exc))
        else:
            if failed:
                status = CustomerSyncRun.Status.PARTIAL
            else:
                status = CustomerSyncRun.Status.SUCCESS

        error_summary = '; '.join(errors[:10])
        finished_at = timezone.now()

        sync_run.status = status
        sync_run.finished_at = finished_at
        sync_run.records_created = created
        sync_run.records_updated = updated
        sync_run.records_skipped = skipped
        sync_run.records_failed = failed
        sync_run.error_summary = error_summary
        sync_run.metadata = {'source_tenant_slug': config.source_tenant_slug}
        sync_run.save(
            update_fields=[
                'status',
                'finished_at',
                'records_created',
                'records_updated',
                'records_skipped',
                'records_failed',
                'error_summary',
                'metadata',
            ]
        )

        config.last_synced_at = finished_at
        config.last_sync_status = (
            ExternalCustomerSyncConfig.SyncStatus.SUCCESS
            if status == CustomerSyncRun.Status.SUCCESS
            else ExternalCustomerSyncConfig.SyncStatus.PARTIAL
            if status == CustomerSyncRun.Status.PARTIAL
            else ExternalCustomerSyncConfig.SyncStatus.FAILED
        )
        config.last_error_message = error_summary
        config.last_success_count = created + updated + skipped
        config.last_failure_count = failed
        config.save(
            update_fields=[
                'last_synced_at',
                'last_sync_status',
                'last_error_message',
                'last_success_count',
                'last_failure_count',
                'updated_at',
            ]
        )

        cls._log_sync_audit(
            company=company,
            initiated_by=initiated_by,
            status=status,
            created=created,
            updated=updated,
            skipped=skipped,
            failed=failed,
            error_summary=error_summary,
        )

        return SyncOutcome(
            run=sync_run,
            created=created,
            updated=updated,
            skipped=skipped,
            failed=failed,
            status=status,
            error_summary=error_summary,
        )

    @classmethod
    @transaction.atomic
    def _upsert_reference(cls, *, company, payload: dict) -> str:
        normalized = cls._normalize_payload(payload)
        reference = ExternalCustomerReference.objects.filter(
            company=company,
            external_uuid=normalized['external_uuid'],
        ).first()

        now = timezone.now()
        if reference is None:
            ExternalCustomerReference.objects.create(
                company=company,
                last_synced_at=now,
                sync_status=ExternalCustomerReference.SyncStatus.SYNCED,
                **normalized,
            )
            return 'created'

        changed = False
        for field in cls.SYNC_FIELDS:
            if getattr(reference, field) != normalized[field]:
                setattr(reference, field, normalized[field])
                changed = True

        reference.last_synced_at = now
        reference.sync_status = ExternalCustomerReference.SyncStatus.SYNCED
        if changed:
            reference.save(update_fields=[*cls.SYNC_FIELDS, 'last_synced_at', 'sync_status', 'updated_at'])
            return 'updated'

        reference.save(update_fields=['last_synced_at', 'sync_status', 'updated_at'])
        return 'skipped'

    @staticmethod
    def _normalize_payload(payload: dict) -> dict:
        external_uuid = payload.get('uuid')
        created_at = parse_datetime(payload.get('created_at', '')) if payload.get('created_at') else None
        if not external_uuid or created_at is None:
            raise ValueError('Customer payload missing uuid or created_at.')

        return {
            'external_uuid': external_uuid,
            'full_name': (payload.get('full_name') or '').strip(),
            'phone': (payload.get('phone') or '').strip(),
            'email': (payload.get('email') or '').strip(),
            'address': (payload.get('address') or '').strip(),
            'customer_status': (payload.get('customer_status') or '').strip(),
            'customer_type': (payload.get('customer_type') or '').strip(),
            'source_created_at': created_at,
        }

    @staticmethod
    def _log_sync_audit(*, company, initiated_by, status, created, updated, skipped, failed, error_summary):
        details = (
            f'Customer sync {status}. Created: {created}, updated: {updated}, '
            f'skipped: {skipped}, failed: {failed}.'
        )
        log_audit(
            user=initiated_by,
            action='edit',
            asset=None,
            details=details,
            company=company,
            metadata={
                'integration': 'external_customer_sync',
                'status': status,
                'records_created': created,
                'records_updated': updated,
                'records_skipped': skipped,
                'records_failed': failed,
                'error_summary': error_summary,
            },
        )
