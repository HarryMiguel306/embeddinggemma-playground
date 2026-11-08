
import json
import os
import random
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from google import genai

from apps.catalog.models import Category, Product

import time


# ==================================================
# 1. QUOTAS DU CATALOGUE
# ==================================================

CATEGORY_QUOTAS = {
    "Vêtements & mode": 90,
    "Chaussures & accessoires": 65,
    "Beauté & soins": 65,
    "Bijoux & artisanat": 55,
    "Maison & décoration": 60,
    "Électronique & gadgets": 55,
    "Alimentation & épicerie": 45,
    "Sport & loisirs": 35,
    "Livres & papeterie": 30,
}

COUNTRY_QUOTAS = {
    "BJ": 150,
    "CI": 90,
    "SN": 70,
    "TG": 50,
    "GH": 40,
    "NG": 35,
    "CM": 12,
    "BF": 10,
    "ML": 10,
    "NE": 8,
    "FR": 25,
}

COUNTRY_NAMES = {
    "BJ": "Bénin",
    "CI": "Côte d'Ivoire",
    "SN": "Sénégal",
    "TG": "Togo",
    "GH": "Ghana",
    "NG": "Nigeria",
    "CM": "Cameroun",
    "BF": "Burkina Faso",
    "ML": "Mali",
    "NE": "Niger",
    "FR": "France",
}

# Catégories particulièrement adaptées à certains pays.
# Les autres associations restent possibles.
COUNTRY_CATEGORY_PREFERENCES = {
    "BJ": [
        "Alimentation & épicerie",
        "Vêtements & mode",
        "Bijoux & artisanat",
        "Beauté & soins",
        "Maison & décoration",
    ],
    "CI": [
        "Beauté & soins",
        "Alimentation & épicerie",
        "Vêtements & mode",
        "Électronique & gadgets",
    ],
    "SN": [
        "Vêtements & mode",
        "Alimentation & épicerie",
        "Livres & papeterie",
        "Sport & loisirs",
    ],
    "TG": [
        "Vêtements & mode",
        "Bijoux & artisanat",
        "Chaussures & accessoires",
        "Alimentation & épicerie",
    ],
    "GH": [
        "Maison & décoration",
        "Bijoux & artisanat",
        "Vêtements & mode",
        "Chaussures & accessoires",
    ],
    "NG": [
        "Beauté & soins",
        "Électronique & gadgets",
        "Vêtements & mode",
        "Alimentation & épicerie",
    ],
    "CM": [
        "Alimentation & épicerie",
        "Vêtements & mode",
        "Beauté & soins",
        "Maison & décoration",
    ],
    "BF": [
        "Vêtements & mode",
        "Bijoux & artisanat",
        "Alimentation & épicerie",
        "Maison & décoration",
    ],
    "ML": [
        "Alimentation & épicerie",
        "Vêtements & mode",
        "Bijoux & artisanat",
        "Livres & papeterie",
    ],
    "NE": [
        "Alimentation & épicerie",
        "Vêtements & mode",
        "Maison & décoration",
        "Sport & loisirs",
    ],
    "FR": [
        "Livres & papeterie",
        "Électronique & gadgets",
        "Vêtements & mode",
        "Beauté & soins",
    ],
}


# ==================================================
# 2. CALCUL DES QUOTAS RESTANTS
# ==================================================

def get_remaining_quotas():

    category_remaining = {}
    country_remaining = {}

    for category_name, target in CATEGORY_QUOTAS.items():

        existing = Product.objects.filter(
            category__name=category_name
        ).count()

        category_remaining[category_name] = max(
            target - existing, 0
        )

    for country_code, target in COUNTRY_QUOTAS.items():

        existing = Product.objects.filter(
            country_code=country_code
        ).count()

        country_remaining[country_code] = max(
            target - existing, 0
        )

    return category_remaining, country_remaining


# ==================================================
# 3. CONSTRUCTION DU PLAN DE GÉNÉRATION
# ==================================================

def build_generation_plan(category_remaining, country_remaining):

    category_total = sum(category_remaining.values())
    country_total = sum(country_remaining.values())

    if category_total != country_total:
        raise CommandError(
            "Les quotas restants des catégories et des pays "
            "ne correspondent pas. Vérifie les produits "
            "existants et les quotas."
        )

    plan = []

    categories = dict(category_remaining)
    countries = dict(country_remaining)

    while sum(countries.values()) > 0:

        possible_pairs = []

        for country, country_quantity in countries.items():

            if country_quantity <= 0:
                continue

            preferences = COUNTRY_CATEGORY_PREFERENCES[country]

            for category, category_quantity in categories.items():

                if category_quantity <= 0:
                    continue

                if category in preferences:
                    preference_score = (
                        len(preferences) - preferences.index(category)
                    )
                else:
                    preference_score = 0

                possible_pairs.append((
                    preference_score,
                    country,
                    category,
                ))

        if not possible_pairs:
            raise CommandError(
                "Impossible de construire le plan de génération."
            )

        best_score = max(pair[0] for pair in possible_pairs)

        best_pairs = [
            pair for pair in possible_pairs
            if pair[0] == best_score
        ]

        _, country, category = random.choice(best_pairs)

        plan.append({
            "category": category,
            "country_code": country,
        })

        countries[country] -= 1
        categories[category] -= 1

    random.shuffle(plan)

    return plan


# ==================================================
# 4. COMMANDE DJANGO
# ==================================================

class Command(BaseCommand):

    help = "Génère le catalogue synthétique avec Gemini"

    def add_arguments(self, parser):

        parser.add_argument(
            "--total",
            type=int,
            default=None,
            help="Nombre de produits à générer.",
        )

        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Nombre de produits par requête Gemini.",
        )

    def handle(self, *args, **options):

        requested_total = options["total"]
        batch_size = options["batch_size"]

        if requested_total is not None and requested_total < 1:
            raise CommandError("Le total doit être positif.")

        if batch_size < 1 or batch_size > 20:
            raise CommandError(
                "La taille du lot doit être comprise entre 1 et 20."
            )

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise CommandError("GEMINI_API_KEY est introuvable.")

        category_remaining, country_remaining = get_remaining_quotas()

        available = sum(category_remaining.values())

        if available == 0:
            raise CommandError(
                "Tous les quotas sont déjà atteints."
            )

        total_countries = sum(country_remaining.values())

        if available != total_countries:
            raise CommandError(
                f"Incohérence des quotas : {available} produits "
                f"restants par catégorie contre {total_countries} "
                "par pays."
            )

        total = (
            requested_total
            if requested_total is not None
            else available
        )

        if total > available:
            raise CommandError(
                f"Tu demandes {total} produits, mais seulement "
                f"{available} restent à générer."
            )

        plan = build_generation_plan(
            category_remaining,
            country_remaining,
        )

        plan = plan[:total]

        self.stdout.write(
            self.style.NOTICE(
                f"Produits à générer : {total}"
            )
        )

        self.stdout.write(
            f"Produits déjà enregistrés : {Product.objects.count()}"
        )

        self.stdout.write(
            f"Lots prévus : {(total + batch_size - 1) // batch_size}"
        )

        client = genai.Client(api_key=api_key)

        created_total = 0

        try:

            for start in range(0, total, batch_size):

                batch = plan[start:start + batch_size]

                self.stdout.write(
                    self.style.NOTICE(
                        f"\nLot {start // batch_size + 1} "
                        f"({len(batch)} produits)"
                    )
                )

                created = self.generate_batch(client, batch)

                created_total += created

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Progression : {created_total}/{total}"
                    )
                )

        finally:
            try:
                client.close()
            except AttributeError:
                pass

        self.stdout.write("\n" + "=" * 45)

        self.stdout.write(
            self.style.SUCCESS(
                f"Produits créés : {created_total}"
            )
        )

        self.stdout.write(
            f"Total actuel : {Product.objects.count()}/500"
        )

        self.stdout.write("=" * 45)

        self.display_remaining_quotas()


    # ==================================================
    # 5. GÉNÉRATION D'UN LOT
    # ==================================================

    def generate_batch(self, client, batch):

        existing_names = list(
            Product.objects.values_list("name", flat=True)
        )

        assignments = []

        for index, assignment in enumerate(batch, start=1):

            country_code = assignment["country_code"]

            assignments.append({
                "numero": index,
                "categorie": assignment["category"],
                "pays": COUNTRY_NAMES[country_code],
                "country_code": country_code,
            })

        prompt = f"""
Tu es un expert en création de catalogues e-commerce.

Génère exactement {len(batch)} produits fictifs.

CONTEXTE GÉNÉRAL :

- Le catalogue est majoritairement africain.
- Tous les textes doivent être en français.
- Les produits et les marques sont fictifs.
- Les produits doivent être crédibles et commercialisables.
- Les descriptions doivent être naturelles et détaillées.
- Chaque description contient au moins deux phrases.
- Les prix sont exprimés en FCFA.
- La devise utilisée sera toujours XOF.
- Évite les répétitions de noms, marques et descriptions.

COHÉRENCE GÉOGRAPHIQUE :

Le code pays indique le pays d'origine du produit.

Adapte les produits au contexte du pays concerné :
- matériaux et savoir-faire locaux ;
- styles vestimentaires et artisanaux pertinents ;
- habitudes de consommation et usages plausibles ;
- références géographiques pertinentes.

N'invente pas de traditions ou de références culturelles.
Ne prétends pas qu'un produit est fabriqué localement
si sa description ne permet pas de le justifier.

ATTRIBUTIONS OBLIGATOIRES :

Voici les produits à générer.
Chaque ligne correspond à un produit précis.

{json.dumps(assignments, ensure_ascii=False, indent=2)}

Respecte exactement la catégorie et le pays de chaque ligne.
Ne permute pas les attributions.

NOMS DÉJÀ UTILISÉS :

{json.dumps(existing_names, ensure_ascii=False)}

FORMAT JSON OBLIGATOIRE :

Retourne uniquement un tableau JSON valide.

Chaque objet contient exactement ces six champs :

{{
    "name": "Nom du produit",
    "description": "Description détaillée en français",
    "category": "Catégorie attribuée",
    "brand": "Marque fictive",
    "price": 12500,
    "country_code": "BJ"
}}
"""

        max_attempts = 5
        response = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                    },
                )
                break

            except Exception as error:
                error_message = str(error).upper()

                temporary_errors = [
                    "503",
                    "UNAVAILABLE",
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "500",
                    "INTERNAL",
                ]

                is_temporary = any(
                    code in error_message
                    for code in temporary_errors
                )

                if not is_temporary or attempt == max_attempts:
                    raise CommandError(
                        f"Erreur Gemini après {attempt} tentative(s) : {error}"
                    )

                wait_time = min(3 * (2 ** (attempt - 1)), 30)

                self.stdout.write(
                    self.style.WARNING(
                        f"Gemini temporairement indisponible. "
                        f"Tentative {attempt}/{max_attempts}. "
                        f"Nouvel essai dans {wait_time} secondes..."
                    )
                )

                time.sleep(wait_time)

        if response is None:
            raise CommandError("Gemini n'a retourné aucune réponse.")

        if not response.text:
            raise CommandError(
                "Gemini a retourné une réponse vide."
            )

        try:
            products_data = json.loads(response.text)

        except json.JSONDecodeError:
            raise CommandError(
                "Gemini n'a pas retourné un JSON valide."
            )

        if not isinstance(products_data, list):
            raise CommandError(
                "La réponse Gemini doit être un tableau JSON."
            )

        if len(products_data) != len(batch):
            raise CommandError(
                f"Gemini a retourné {len(products_data)} produits "
                f"au lieu de {len(batch)}."
            )

        validated_products = []
        batch_names = set()

        for index, (item, assignment) in enumerate(
            zip(products_data, batch),
            start=1,
        ):

            required_fields = {
                "name",
                "description",
                "category",
                "brand",
                "price",
                "country_code",
            }

            if not isinstance(item, dict):
                raise CommandError(
                    f"Le produit {index} n'est pas un objet JSON."
                )

            if set(item.keys()) != required_fields:
                raise CommandError(
                    f"Les champs du produit {index} sont incorrects."
                )

            name = str(item["name"]).strip()
            description = str(item["description"]).strip()
            category_name = str(item["category"]).strip()
            brand = str(item["brand"]).strip()
            country_code = str(item["country_code"]).strip().upper()

            if not name or not description or not brand:
                raise CommandError(
                    f"Le produit {index} contient un champ vide."
                )

            if category_name != assignment["category"]:
                raise CommandError(
                    f"Mauvaise catégorie pour le produit {index}."
                )

            if country_code != assignment["country_code"]:
                raise CommandError(
                    f"Mauvais pays pour le produit {index}."
                )

            if len(name) > 200 or len(brand) > 100:
                raise CommandError(
                    f"Nom ou marque trop long pour le produit {index}."
                )

            if len(description) < 30:
                raise CommandError(
                    f"Description trop courte pour le produit {index}."
                )

            try:

                price = Decimal(str(item["price"]))

                if not price.is_finite() or price <= 0:
                    raise InvalidOperation

                if price > Decimal("9999999999.99"):
                    raise InvalidOperation

                price = price.quantize(Decimal("0.01"))

            except (InvalidOperation, ValueError, TypeError):
                raise CommandError(
                    f"Prix invalide pour le produit {index}."
                )

            if name.casefold() in batch_names:
                raise CommandError(
                    f"Nom dupliqué dans le lot : {name}"
                )

            if Product.objects.filter(name__iexact=name).exists():
                raise CommandError(
                    f"Ce produit existe déjà : {name}"
                )

            batch_names.add(name.casefold())

            validated_products.append({
                "name": name,
                "description": description,
                "category": category_name,
                "brand": brand,
                "price": price,
                "country_code": country_code,
            })

        # Enregistrement atomique :
        # aucun produit du lot n'est enregistré si une erreur survient.
        with transaction.atomic():

            for item in validated_products:

                category, _ = Category.objects.get_or_create(
                    slug=slugify(item["category"]),
                    defaults={
                        "name": item["category"],
                        "description": (
                            f"Produits de la catégorie "
                            f"{item['category']}."
                        ),
                    },
                )

                Product.objects.create(
                    name=item["name"],
                    description=item["description"],
                    category=category,
                    brand=item["brand"],
                    price=item["price"],
                    currency="XOF",
                    country_code=item["country_code"],
                    is_active=True,
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Créé : {item['name']}"
                    )
                )

        return len(validated_products)


    # ==================================================
    # 6. AFFICHAGE DES QUOTAS RESTANTS
    # ==================================================

    def display_remaining_quotas(self):

        category_remaining, country_remaining = get_remaining_quotas()

        self.stdout.write("\nQUOTAS RESTANTS PAR CATÉGORIE")

        for category, quantity in category_remaining.items():
            self.stdout.write(f"{category} : {quantity}")

        self.stdout.write("\nQUOTAS RESTANTS PAR PAYS")

        for country, quantity in country_remaining.items():
            self.stdout.write(
                f"{COUNTRY_NAMES[country]} : {quantity}"
            )
