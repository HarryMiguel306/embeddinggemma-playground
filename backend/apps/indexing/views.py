from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.catalog.models import Product
from apps.embeddings.models import Embedding
from apps.embeddings.services import EmbeddingService
from .models import IndexingTask
from .services import get_client, ensure_index, index_product


class IndexingTaskListView(generics.ListAPIView):
    """Liste des tâches d'indexation."""

    def list(self, request, *args, **kwargs):
        queryset = IndexingTask.objects.all().order_by('-created_at')
        data = [
            {
                'id': str(t.id),
                'status': t.status,
                'total_products': t.total_products,
                'indexed_products': t.indexed_products,
                'error_message': t.error_message,
                'created_at': t.created_at,
                'started_at': t.started_at,
                'finished_at': t.finished_at,
            }
            for t in queryset
        ]
        return Response(data)


class IndexingRunView(APIView):
    """Lance l'indexation de tous les produits ayant un embedding terminé.

    Utilise le vecteur déjà stocké en base pour éviter le ré-encodage
    (et donc éviter les problèmes de mémoire sur les gros catalogues).
    """

    def post(self, request):
        limit = int(request.data.get('limit', 0) or 0)

        task = IndexingTask.objects.create()
        task.mark_running()

        try:
            client = get_client()
            ensure_index(client)

            embeddings = Embedding.objects.filter(
                status=Embedding.STATUS_DONE,
            ).select_related('product')

            if limit:
                embeddings = embeddings[:limit]

            task.total_products = embeddings.count()
            task.save()

            indexed = 0
            errors = []

            for emb in embeddings:
                product = emb.product
                try:
                    # Utilise le vecteur déjà stocké, pas besoin de ré-encoder
                    vector = emb.vector
                    if vector is None:
                        # Fallback : encode si pas stocké
                        vector = EmbeddingService.encode_product(product)

                    index_product(product, vector, client=client)
                    emb.elasticsearch_id = str(product.id)
                    emb.save(update_fields=['elasticsearch_id'])
                    indexed += 1
                    task.indexed_products = indexed
                    task.save(update_fields=['indexed_products'])
                except Exception as exc:
                    errors.append({
                        'product_id': str(product.id),
                        'product_name': product.name,
                        'error': str(exc),
                    })

            client.close()
            task.mark_done()

            return Response({
                'id': str(task.id),
                'status': task.status,
                'total_products': task.total_products,
                'indexed_products': task.indexed_products,
                'errors': errors,
            }, status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS)
        except Exception as exc:
            task.mark_error(str(exc))
            return Response(
                {'error': str(exc), 'task_id': str(task.id)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
