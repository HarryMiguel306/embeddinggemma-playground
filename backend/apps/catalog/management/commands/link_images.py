import json
import os
from django.core.management.base import BaseCommand
from django.core.files import File
from django.db import transaction
from apps.catalog.models import Product, ProductImage


class Command(BaseCommand):
    help = "Lie des images physiques aux produits existants selon un fichier de mapping JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mapping",
            type=str,
            default="image_mapping.json",
            help="Chemin vers le fichier JSON de correspondance.",
        )
        parser.add_argument(
            "--images-dir",
            type=str,
            default="media/products",
            help="Dossier contenant les images physiques.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simule sans écrire en base.",
        )

    def handle(self, *args, **options):
        mapping_path = options["mapping"]
        images_dir = options["images_dir"]
        dry_run = options["dry_run"]

        if not os.path.exists(mapping_path):
            self.stderr.write(self.style.ERROR(f"Fichier introuvable : {mapping_path}"))
            return

        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        created = 0
        skipped = 0
        errors = 0

        with transaction.atomic():
            for entry in mapping:
                product_id = entry.get("product_id")
                image_file = entry.get("image_file")
                is_primary = entry.get("is_primary", False)
                position = entry.get("position", 1)

                if not image_file:
                    self.stdout.write(f"⏭️  Pas de fichier pour {product_id}, ignoré.")
                    skipped += 1
                    continue

                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"Produit introuvable : {product_id}"))
                    errors += 1
                    continue

                image_path = image_file if os.path.isabs(image_file) else os.path.join(images_dir, image_file)

                if not os.path.exists(image_path):
                    self.stderr.write(self.style.ERROR(f"Image introuvable : {image_path}"))
                    errors += 1
                    continue

                if is_primary:
                    ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)

                if not dry_run:
                    with open(image_path, "rb") as img_file:
                        product_image = ProductImage(
                            product=product,
                            alt_text=f"Image de {product.name}",
                            position=position,
                            is_primary=is_primary,
                        )
                        product_image.image.save(
                            os.path.basename(image_file),
                            File(img_file),
                            save=True,
                        )
                created += 1

        if dry_run:
            # Rollback de la transaction pour le dry-run
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("[DRY RUN] Aucun enregistrement écrit en base."))

        self.stdout.write(
            self.style.SUCCESS(f"{created} image(s) liée(s). {skipped} ignoré(s). {errors} erreur(s).")
        )
