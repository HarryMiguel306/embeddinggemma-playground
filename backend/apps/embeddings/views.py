from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.catalog.models import Product
from .models import Embedding
from .services import EmbeddingService


class EmbeddingListView(generics.ListAPIView):
    """Liste des embeddings avec leur statut."""

    queryset = Embedding.objects.select_related('product').all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = [
            {
                'id': str(e.id),
                'product_id': str(e.product.id),
                'product_name': e.product.name,
                'model_name': e.model_name,
                'dimension': e.dimension,
                'status': e.status,
                'elasticsearch_id': e.elasticsearch_id,
                'error_message': e.error_message,
                'created_at': e.created_at,
                'updated_at': e.updated_at,
            }
            for e in queryset
        ]
        return Response(data)


class EmbeddingGenerateView(APIView):
    """Génère (ou régénère) l'embedding d'un produit donné.

    Corps attendu : {"product_id": "<uuid>"}
    """

    def post(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response(
                {'error': 'product_id est requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Produit introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        embedding, _ = Embedding.objects.get_or_create(product=product)

        try:
            vector = EmbeddingService.encode_product(product)
            content_hash = EmbeddingService.compute_content_hash(product)

            embedding.content_hash = content_hash
            embedding.dimension = len(vector)
            # L'ID Elasticsearch est renseigné lors de l'indexation.
            embedding.mark_done(elasticsearch_id=embedding.elasticsearch_id)

            return Response({
                'id': str(embedding.id),
                'product_id': str(product.id),
                'dimension': embedding.dimension,
                'status': embedding.status,
                'vector_preview': vector[:5],
            })
        except Exception as exc:  # pragma: no cover - dépend de l'env local
            embedding.mark_error(str(exc))
            return Response(
                {'error': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
