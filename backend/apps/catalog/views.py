from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework import generics, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, JSONParser

from .models import Category, Product, ProductImage
from .serializers import CategorySerializer, CategoryListSerializer, ProductSerializer, ProductCreateSerializer
from apps.embeddings.models import Embedding
from apps.embeddings.services import EmbeddingService
from apps.indexing.services import index_product


class CategoryListView(generics.ListAPIView):
    """Liste toutes les catégories avec le nombre de produits associé."""

    serializer_class = CategoryListSerializer

    def get_queryset(self):
        return Category.objects.annotate(product_count=Count('products')).order_by('name')


class CategoryDetailView(generics.RetrieveAPIView):
    """Détail d'une catégorie."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'


class ProductListView(generics.ListAPIView):
    """Liste des produits avec filtres et recherche textuelle basique.

    Paramètres de filtre acceptés :
    - category (slug ou ID)
    - country_code
    - is_active (true/false)
    - search (recherche dans nom, description, marque)
    - ordering (prix, name, created_at)
    """

    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'brand']
    ordering_fields = ['price', 'name', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)

        country_code = self.request.query_params.get('country_code')
        if country_code:
            queryset = queryset.filter(country_code=country_code.upper())

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    """Détail complet d'un produit avec ses images."""

    queryset = Product.objects.select_related('category').prefetch_related('images').all()
    serializer_class = ProductSerializer
    lookup_field = 'pk'


class ProductCreateView(APIView):
    """Créer une fiche produit manuellement.

    Accepte JSON ou multipart/form-data (avec un champ image optionnel).
    Après création, génère l'embedding et indexe le produit dans Elasticsearch.
    """
    parser_classes = [MultiPartParser, JSONParser]

    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image_file = serializer.validated_data.pop('image', None)
        product = serializer.save()

        # Lier l'image si fournie
        if image_file:
            ProductImage.objects.create(
                product=product,
                image=image_file,
                alt_text=f"Image de {product.name}",
                position=1,
                is_primary=True,
            )

        # Générer l'embedding
        embedding_id = None
        vector = None
        try:
            embedding, _ = Embedding.objects.get_or_create(product=product)
            primary_image = product.images.filter(is_primary=True).first()
            image_bytes = None
            if primary_image and primary_image.image:
                with primary_image.image.open('rb') as f:
                    image_bytes = f.read()

            vector = EmbeddingService.encode_product(product, image_bytes=image_bytes)
            content_hash = EmbeddingService.compute_content_hash(product)

            embedding.mark_done(
                elasticsearch_id=embedding.elasticsearch_id,
                vector=vector,
            )
            embedding_id = str(embedding.id)
        except Exception as exc:
            # On continue même si l'embedding échoue (produit créé quand même)
            pass

        # Indexer dans Elasticsearch
        es_indexed = False
        if vector is not None:
            try:
                es_id = index_product(product, vector)
                if embedding_id:
                    emb = Embedding.objects.get(id=embedding_id)
                    emb.elasticsearch_id = es_id
                    emb.save(update_fields=['elasticsearch_id'])
                es_indexed = True
            except Exception as exc:
                # Elasticsearch pas encore lancé ou erreur d'indexation
                pass

        data = ProductSerializer(product).data
        data['embedding_created'] = embedding_id is not None
        data['elasticsearch_indexed'] = es_indexed

        return Response(data, status=status.HTTP_201_CREATED)
