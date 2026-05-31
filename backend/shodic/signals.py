import logging

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import RawSourceData

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=RawSourceData)
def delete_raw_source_vectors(sender, instance, **kwargs):
    point_ids = list(
        instance.chunks.exclude(qdrant_point_id__isnull=True)
        .exclude(qdrant_point_id='')
        .values_list('qdrant_point_id', flat=True)
    )
    if not point_ids:
        return

    from .qdrant_service import delete_points  # noqa: PLC0415

    deleted_count = delete_points(point_ids)
    logger.info(
        "Deleted %s Qdrant point(s) for raw source %s.",
        deleted_count,
        instance.pk,
    )
