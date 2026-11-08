import hashlib
from typing import List, Optional, Union

import numpy as np

from apps.catalog.models import Product


class EmbeddingService:
    """Service de génération d'embeddings avec un modèle léger (all-MiniLM-L6-v2).

    Le modèle est chargé à la demande et mis en cache en mémoire pour éviter
    de le recharger à chaque opération. Le traitement s'effectue sur CPU
    en précision float32 avec des vecteurs de 256 dimensions (tronqués depuis
    les 384 dimensions natives du modèle).
    """

    _model = None
    _model_name = 'sentence-transformers/all-MiniLM-L6-v2'
    _dimension = 256

    @classmethod
    def get_model(cls):
        """Charge et retourne le modèle Sentence Transformers (mis en cache)."""
        if cls._model is None:
            from sentence_transformers import SentenceTransformer

            cls._model = SentenceTransformer(cls._model_name, trust_remote_code=True)
            cls._model.eval()
        return cls._model

    @classmethod
    def compute_content_hash(cls, product: Product) -> str:
        """Calcule une empreinte du contenu textuel d'un produit.

        Permet de détecter si une fiche a changé et doit être ré-encodée.
        """
        parts = [
            product.name or '',
            product.category.name if product.category else '',
            product.brand or '',
            product.description or '',
            str(product.price),
            product.currency,
            product.country_code,
        ]
        content = ' | '.join(parts)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @classmethod
    def build_product_text(cls, product: Product) -> str:
        """Construit la représentation textuelle structurée d'un produit."""
        return (
            f"Nom : {product.name}. "
            f"Catégorie : {product.category.name if product.category else ''}. "
            f"Marque : {product.brand or ''}. "
            f"Description : {product.description}. "
            f"Prix : {product.price} {product.currency}. "
            f"Pays d'origine : {product.country_code}."
        )

    @classmethod
    def encode_text(cls, text: str) -> List[float]:
        """Encode un texte brut en vecteur de 256 dimensions (float32)."""
        model = cls.get_model()
        embedding = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return cls._truncate(embedding).astype(np.float32).tolist()

    @classmethod
    def _truncate(cls, embedding: np.ndarray) -> np.ndarray:
        """Tronque ou pad le vecteur à la dimension cible (256)."""
        if embedding.ndim > 1:
            embedding = embedding.reshape(-1)
        current_dim = embedding.shape[0]
        if current_dim > cls._dimension:
            return embedding[: cls._dimension]
        elif current_dim < cls._dimension:
            padded = np.zeros(cls._dimension, dtype=np.float32)
            padded[:current_dim] = embedding
            return padded
        return embedding

    @classmethod
    def encode_product(
        cls,
        product: Product,
        image_bytes: Optional[bytes] = None,
    ) -> List[float]:
        """Encode une fiche produit en un embedding textuel.

        Le modèle all-MiniLM-L6-v2 est textuel uniquement. L'image est
        acceptée en paramètre pour l'interface mais ignorée par le modèle
        actuel (à faire évoluer vers un modèle multimodal plus tard).
        """
        text = cls.build_product_text(product)
        model = cls.get_model()
        embedding = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return cls._truncate(embedding).astype(np.float32).tolist()
