from celery import shared_task

from tenancy.models import Company

from .models import ExternalCustomerReference
from .services import CustomerAssetProjectionService, SourceCustomerApiError


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def sync_customer_asset_projection(self, reference_id):
    try:
        return CustomerAssetProjectionService.sync_reference(reference_id=reference_id)
    except ExternalCustomerReference.DoesNotExist:
        return {'skipped': 'customer reference no longer exists'}
    except SourceCustomerApiError as exc:
        raise self.retry(exc=exc, countdown=min(60 * (2 ** self.request.retries), 3600))


@shared_task
def enqueue_company_asset_projections(company_id):
    reference_ids = ExternalCustomerReference.objects.filter(company_id=company_id).values_list('id', flat=True)
    queued = 0
    for reference_id in reference_ids.iterator(chunk_size=500):
        sync_customer_asset_projection.delay(reference_id)
        queued += 1
    return {'company_id': company_id, 'queued': queued}


@shared_task
def enqueue_all_asset_projections():
    company_ids = Company.objects.filter(
        external_customer_sync_config__is_enabled=True,
    ).values_list('id', flat=True)
    queued = 0
    for company_id in company_ids.iterator(chunk_size=100):
        enqueue_company_asset_projections.delay(company_id)
        queued += 1
    return {'companies_queued': queued}
