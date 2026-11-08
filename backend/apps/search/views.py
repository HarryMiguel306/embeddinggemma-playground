from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.parsers import MultiPartParser, JSONParser

from .models import SearchQuery
from .services import search_text, search_image


class SearchTextView(APIView):
    """Recherche sémantique par texte.

    Corps attendu :
    {
        "query": "tenue traditionnelle élégante pour cérémonie",
        "k": 10,
        "category": "vêtements-et-mode",
        "country_code": "BJ",
        "is_active": true,
        "price_min": 5000,
        "price_max": 50000
    }
    """

    parser_classes = [JSONParser]

    def post(self, request):
        query = request.data.get('query', '').strip()
        if not query:
            return Response(
                {'error': 'Le champ "query" est requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            k = int(request.data.get('k', 10))
        except (ValueError, TypeError):
            k = 10

        results = search_text(
            query=query,
            k=k,
            category=request.data.get('category'),
            country_code=request.data.get('country_code'),
            is_active=request.data.get('is_active'),
            price_min=request.data.get('price_min'),
            price_max=request.data.get('price_max'),
        )

        SearchQuery.objects.create(
            query_text=query,
            has_image=False,
            results_count=len(results),
        )

        return Response({
            'query': query,
            'k': k,
            'results_count': len(results),
            'results': results,
        })


class SearchImageView(APIView):
    """Recherche sémantique par image.

    Corps attendu (multipart/form-data) :
    - image : fichier image
    - k (optionnel) : nombre de résultats
    - category, country_code, is_active, price_min, price_max (optionnels)
    """

    parser_classes = [MultiPartParser]

    def post(self, request):
        image_file = request.FILES.get('image')
        if not image_file:
            return Response(
                {'error': 'Le champ "image" est requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            k = int(request.data.get('k', 10))
        except (ValueError, TypeError):
            k = 10

        image_bytes = image_file.read()

        results = search_image(
            image_bytes=image_bytes,
            k=k,
            category=request.data.get('category'),
            country_code=request.data.get('country_code'),
            is_active=request.data.get('is_active'),
            price_min=request.data.get('price_min'),
            price_max=request.data.get('price_max'),
        )

        SearchQuery.objects.create(
            query_text='',
            has_image=True,
            results_count=len(results),
        )

        return Response({
            'k': k,
            'results_count': len(results),
            'results': results,
        })
