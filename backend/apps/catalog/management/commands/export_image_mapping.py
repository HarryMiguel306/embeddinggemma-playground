import json
from django.core.management.base import BaseCommand
from apps.catalog.models import Product


class Command(BaseCommand):
    help = "Génère un template JSON de correspondance produit -> image à remplir."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="image_mapping_template.json",
            help="Chemin du fichier JSON à générer.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=250,
            help="Nombre de produits à inclure dans le template.",
        )

    def handle(self, *args, **options):
        output = options["output"]
        limit = options["limit"]

        products = Product.objects.filter(is_active=True).order_by("created_at")[:limit]

        mapping = []
        for product in products:
            mapping.append({
                "product_id": str(product.id),
                "product_name": product.name,
                "category": product.category.name if product.category else "",
                "country_code": product.country_code,
                "image_file": "",  # <-- à remplir avec le nom du fichier image
                "is_primary": True,
                "position": 1,
            })

        with open(output, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        self.stdout.write(
            self.style.SUCCESS(
                f"Template généré : {output} ({len(mapping)} produits)."
            )
        )
        self.stdout.write(
            "Remplis le champ 'image_file' pour chaque produit avec le nom du fichier image,"
        )
        self.stdout.write(
            "puis lance la commande 'link_images'."
        )
