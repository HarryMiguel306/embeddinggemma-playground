import os
from django.core.management.base import BaseCommand
from django.core.files import File
from apps.catalog.models import Product, ProductImage


class Command(BaseCommand):
    help = "Importe les images depuis media/products/ et les lie aux produits par UUID."

    def add_arguments(self, parser):
        parser.add_argument(
            "--images-dir",
            type=str,
            default="media/products",
            help="Dossier contenant les images (nom de fichier = UUID du produit).",
        )

    def handle(self, *args, **options):
        images_dir = options["images_dir"]

        if not os.path.isdir(images_dir):
            self.stderr.write(self.style.ERROR(f"Dossier introuvable : {images_dir}"))
            return

        fichiers = [
            f for f in os.listdir(images_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        if not fichiers:
            self.stdout.write(self.style.WARNING("Aucune image trouvée."))
            return

        created = 0
        skipped = 0
        errors = 0

        for fichier in fichiers:
            product_id = fichier.rsplit(".", 1)[0]

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                self.stderr.write(self.style.WARNING(f"⚠️  Produit introuvable : {fichier}"))
                errors += 1
                continue

            if ProductImage.objects.filter(product=product).exists():
                self.stdout.write(f"⏭️  Déjà lié : {product.name}")
                skipped += 1
                continue

            image_path = os.path.join(images_dir, fichier)
            try:
                with open(image_path, "rb") as f:
                    ProductImage.objects.create(
                        product=product,
                        image=File(f),
                        alt_text=f"Image de {product.name}",
                        position=1,
                        is_primary=True,
                    )
                created += 1
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"❌ Erreur sur {fichier} : {exc}"))
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ {created} image(s) liée(s). {skipped} ignoré(s). {errors} erreur(s).")
        )
