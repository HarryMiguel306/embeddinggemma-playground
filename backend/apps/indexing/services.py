from typing import List, Dict, Optional

from elasticsearch import Elasticsearch

from django.conf import settings


def get_client() -> Elasticsearch:
    """Retourne un client Elasticsearch configuré."""
    kwargs = {'hosts': [settings.ELASTICSEARCH_HOST]}
    if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
        kwargs['basic_auth'] = (
            settings.ELASTICSEARCH_USERNAME,
            settings.ELASTICSEARCH_PASSWORD,
        )
    return Elasticsearch(**kwargs)


def ensure_index(client: Optional[Elasticsearch] = None) -> Elasticsearch:
    """Crée l'index Elasticsearch s'il n'existe pas, avec un champ dense_vector
    de 256 dimensions, une stratégie HNSW et une similarité cosinus."""
    close_client = False
    if client is None:
        client = get_client()
        close_client = True

    try:
        if client.indices.exists(index=settings.ELASTICSEARCH_INDEX):
            return client

        client.indices.create(
            index=settings.ELASTICSEARCH_INDEX,
            body={
                'settings': {
                    'number_of_shards': 1,
                    'number_of_replicas': 0,
                },
                'mappings': {
                    'properties': {
                        'product_id': {'type': 'keyword'},
                        'name': {'type': 'text', 'analyzer': 'standard'},
                        'description': {'type': 'text', 'analyzer': 'standard'},
                        'category': {'type': 'keyword'},
                        'brand': {'type': 'keyword'},
                        'price': {'type': 'float'},
                        'currency': {'type': 'keyword'},
                        'country_code': {'type': 'keyword'},
                        'is_active': {'type': 'boolean'},
                        'embedding': {
                            'type': 'dense_vector',
                            'dims': settings.ELASTICSEARCH_VECTOR_DIM,
                            'index': True,
                            'similarity': 'cosine',
                        },
                    }
                },
            },
        )
    finally:
        if close_client:
            client.close()

    return client


def index_product(
    product,
    vector: List[float],
    client: Optional[Elasticsearch] = None,
) -> str:
    """Indexe (ou met à jour) un produit dans Elasticsearch.

    Retourne l'ID du document Elasticsearch.
    """
    close_client = False
    if client is None:
        client = get_client()
        close_client = True

    try:
        ensure_index(client)
        doc = {
            'product_id': str(product.id),
            'name': product.name,
            'description': product.description,
            'category': product.category.name if product.category else '',
            'brand': product.brand or '',
            'price': float(product.price),
            'currency': product.currency,
            'country_code': product.country_code,
            'is_active': product.is_active,
            'embedding': vector,
        }
        resp = client.index(
            index=settings.ELASTICSEARCH_INDEX,
            id=str(product.id),
            document=doc,
            refresh=True,
        )
        return resp['_id']
    finally:
        if close_client:
            client.close()


def delete_product(product_id: str, client: Optional[Elasticsearch] = None) -> bool:
    """Supprime un produit de l'index Elasticsearch."""
    close_client = False
    if client is None:
        client = get_client()
        close_client = True

    try:
        client.delete(
            index=settings.ELASTICSEARCH_INDEX,
            id=product_id,
            refresh=True,
        )
        return True
    except Exception:
        return False
    finally:
        if close_client:
            client.close()


def search_by_vector(
    vector: List[float],
    k: int = 10,
    filters: Optional[Dict] = None,
    client: Optional[Elasticsearch] = None,
) -> List[Dict]:
    """Recherche les produits les plus proches d'un vecteur par similarité cosinus.

    Retourne une liste de dictionnaires avec les métadonnées et le score.
    """
    close_client = False
    if client is None:
        client = get_client()
        close_client = True

    try:
        ensure_index(client)

        query = {
            'knn': {
                'field': 'embedding',
                'query_vector': vector,
                'k': k,
                'num_candidates': max(k * 10, 100),
            }
        }

        if filters:
            query['knn']['filter'] = filters

        resp = client.search(
            index=settings.ELASTICSEARCH_INDEX,
            body=query,
        )

        results = []
        for hit in resp['hits']['hits']:
            source = hit['_source']
            results.append({
                'id': hit['_id'],
                'score': hit['_score'],
                'product_id': source.get('product_id'),
                'name': source.get('name'),
                'description': source.get('description'),
                'category': source.get('category'),
                'brand': source.get('brand'),
                'price': source.get('price'),
                'currency': source.get('currency'),
                'country_code': source.get('country_code'),
                'is_active': source.get('is_active'),
            })
        return results
    finally:
        if close_client:
            client.close()
