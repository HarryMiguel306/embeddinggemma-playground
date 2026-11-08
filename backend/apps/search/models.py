import uuid
from django.db import models


class SearchQuery(models.Model):
    """Historique des requêtes de recherche effectuées via l'API."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query_text = models.TextField(blank=True, default='')
    has_image = models.BooleanField(default=False)
    results_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'SearchQuery {self.id} - {self.query_text[:50]}'


class EvaluationQuery(models.Model):
    """Requête de référence pour l'évaluation de pertinence du moteur."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query_text = models.TextField()
    relevant_product_ids = models.JSONField(
        default=list,
        help_text="Liste des UUID de produits jugés pertinents pour cette requête.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'EvaluationQuery {self.id} - {self.query_text[:50]}'
