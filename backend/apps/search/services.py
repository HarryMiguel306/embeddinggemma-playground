from typing import List, Dict, Optional

from PIL import Image
import io

from apps.embeddings.services import EmbeddingService
from apps.indexing.services import search_by_vector


def build_elasticsearch_filters(
    category: Optional[str] = None,
    country_code: Optional[str] = None,
    is_active: Optional[bool] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
) -> Optional[Dict]:
    """Construit un filtre Elasticsearch à partir des paramètres de recherche."""
    filters = []

    if category:
        filters.append({'term': {'category': category}})

    if country_code:
        filters.append({'term': {'country_code': country_code.upper()}})

    if is_active is not None:
        filters.append({'term': {'is_active': is_active}})

    if price_min is not None or price_max is not None:
        range_filter = {}
        if price_min is not None:
            range_filter['gte'] = price_min
        if price_max is not None:
            range_filter['lte'] = price_max
        filters.append({'range': {'price': range_filter}})

    if not filters:
        return None

    return {'bool': {'filter': filters}}


def search_text(
    query: str,
    k: int = 10,
    category: Optional[str] = None,
    country_code: Optional[str] = None,
    is_active: Optional[bool] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
) -> List[Dict]:
    """Recherche sémantique par texte.

    Encode la requête avec EmbeddingGemma 2 puis interroge Elasticsearch.
    """
    vector = EmbeddingService.encode_text(query)
    filters = build_elasticsearch_filters(
        category=category,
        country_code=country_code,
        is_active=is_active,
        price_min=price_min,
        price_max=price_max,
    )
    return search_by_vector(vector=vector, k=k, filters=filters)


def search_image(
    image_bytes: bytes,
    k: int = 10,
    category: Optional[str] = None,
    country_code: Optional[str] = None,
    is_active: Optional[bool] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
) -> List[Dict]:
    """Recherche sémantique par image.

    Encode l'image avec EmbeddingGemma 2 (vision) puis interroge Elasticsearch.
    """
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    # On réutilise le code d'encodage multimodal avec un produit vide pour
    # obtenir le vecteur de l'image seule dans l'espace commun.
    vector = EmbeddingService.encode_text('')  # placeholder si pas de produit
    # Pour une image seule, on encode directement via le modèle sous-jacent
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer('google/embeddinggemma-2', trust_remote_code=True)
    embedding = model.encode(
        image,
        convert_to_numpy=True,
        normalize_embeddings=True,
        truncate_dimension=256,
    )
    vector = embedding.astype('float32').tolist()

    filters = build_elasticsearch_filters(
        category=category,
        country_code=country_code,
        is_active=is_active,
        price_min=price_min,
        price_max=price_max,
    )
    return search_by_vector(vector=vector, k=k, filters=filters)
