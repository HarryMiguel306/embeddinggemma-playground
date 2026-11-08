import uuid

from django.db import models
from django.utils import timezone


class Embedding(models.Model):
    """Suivi des embeddings générés pour chaque produit."""

    STATUS_PENDING = 'pending'
    STATUS_DONE = 'done'
    STATUS_ERROR = 'error'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_DONE, 'Terminé'),
        (STATUS_ERROR, 'Erreur'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='embedding',
    )
    model_name = models.CharField(max_length=200, default='google/embeddinggemma-2')
    dimension = models.PositiveIntegerField(default=256)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    elasticsearch_id = models.CharField(max_length=200, blank=True, default='')
    content_hash = models.CharField(max_length=64, blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    vector = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Embedding {self.product.name} ({self.status})'

    def mark_done(self, elasticsearch_id: str = '', vector: list = None):
        self.status = self.STATUS_DONE
        self.elasticsearch_id = elasticsearch_id
        self.error_message = ''
        if vector is not None:
            self.vector = vector
            self.dimension = len(vector)
        self.updated_at = timezone.now()
        self.save()

    def mark_error(self, message: str):
        self.status = self.STATUS_ERROR
        self.error_message = message
        self.updated_at = timezone.now()
        self.save()
