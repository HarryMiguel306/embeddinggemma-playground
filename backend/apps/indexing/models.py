import uuid

from django.db import models
from django.utils import timezone


class IndexingTask(models.Model):
    """Suivi des tâches d'indexation des produits dans Elasticsearch."""

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_DONE = 'done'
    STATUS_ERROR = 'error'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_RUNNING, 'En cours'),
        (STATUS_DONE, 'Terminé'),
        (STATUS_ERROR, 'Erreur'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    total_products = models.PositiveIntegerField(default=0)
    indexed_products = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'IndexingTask {self.id} ({self.status})'

    def mark_running(self):
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.error_message = ''
        self.save()

    def mark_done(self):
        self.status = self.STATUS_DONE
        self.finished_at = timezone.now()
        self.save()

    def mark_error(self, message: str):
        self.status = self.STATUS_ERROR
        self.finished_at = timezone.now()
        self.error_message = message
        self.save()
