from django.core.management.base import BaseCommand
from apps.catalog.models import Product
from apps.embeddings.models import Embedding
from apps.embeddings.services import EmbeddingService


class Command(BaseCommand):
    help = "Génère (ou régénère) les embeddings pour tous les produits sans embedding valide."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Nombre maximum de produits à traiter (0 = tous).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Régénère même si un embedding existe déjà.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        force = options["force"]

        queryset = Product.objects.filter(is_active=True).select_related("category")

        if not force:
            queryset = queryset.exclude(embedding__status=Embedding.STATUS_DONE)

        if limit:
            queryset = queryset[:limit]

        total = queryset.count()
        self.stdout.write(f"{total} produit(s) à encoder.")

        created = 0
        errors = 0

        for product in queryset:
            embedding, _ = Embedding.objects.get_or_create(product=product)

            if embedding.status == Embedding.STATUS_DONE and not force:
                continue

            try:
                # Récupère l'image principale si elle existe
                primary_image = product.images.filter(is_primary=True).first()
                image_bytes = None
                if primary_image and primary_image.image:
                    with primary_image.image.open("rb") as f:
                        image_bytes = f.read()

                vector = EmbeddingService.encode_product(product, image_bytes=image_bytes)
                content_hash = EmbeddingService.compute_content_hash(product)

                embedding.mark_done(
                    elasticsearch_id=embedding.elasticsearch_id,
                    vector=vector,
                )

                created += 1
                self.stdout.write(self.style.SUCCESS(f"✅ {product.name} ({len(vector)} dims)"))

            except Exception as exc:
                embedding.status = Embedding.STATUS_ERROR
                embedding.error_message = str(exc)
                embedding.save()
                errors += 1
                self.stderr.write(self.style.ERROR(f"❌ {product.name} : {exc}"))

        self.stdout.write(
            self.style.SUCCESS(f"Terminé : {created} succès, {errors} erreur(s).")
        )
