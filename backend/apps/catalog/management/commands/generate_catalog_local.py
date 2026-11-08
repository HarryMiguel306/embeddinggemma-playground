import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.catalog.models import Category, Product


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
    "BJ": 150, "CI": 90, "SN": 70, "TG": 50, "GH": 40,
    "NG": 35, "CM": 12, "BF": 10, "ML": 10, "NE": 8, "FR": 25,
}

COUNTRY_NAMES = {
    "BJ": "Bénin", "CI": "Côte d'Ivoire", "SN": "Sénégal", "TG": "Togo",
    "GH": "Ghana", "NG": "Nigeria", "CM": "Cameroun", "BF": "Burkina Faso",
    "ML": "Mali", "NE": "Niger", "FR": "France",
}

COUNTRY_CATEGORY_PREFERENCES = {
    "BJ": ["Alimentation & épicerie", "Vêtements & mode", "Bijoux & artisanat", "Beauté & soins", "Maison & décoration"],
    "CI": ["Beauté & soins", "Alimentation & épicerie", "Vêtements & mode", "Électronique & gadgets"],
    "SN": ["Vêtements & mode", "Alimentation & épicerie", "Livres & papeterie", "Sport & loisirs"],
    "TG": ["Vêtements & mode", "Bijoux & artisanat", "Chaussures & accessoires", "Alimentation & épicerie"],
    "GH": ["Maison & décoration", "Bijoux & artisanat", "Vêtements & mode", "Chaussures & accessoires"],
    "NG": ["Beauté & soins", "Électronique & gadgets", "Vêtements & mode", "Alimentation & épicerie"],
    "CM": ["Alimentation & épicerie", "Vêtements & mode", "Beauté & soins", "Maison & décoration"],
    "BF": ["Vêtements & mode", "Bijoux & artisanat", "Alimentation & épicerie", "Maison & décoration"],
    "ML": ["Alimentation & épicerie", "Vêtements & mode", "Bijoux & artisanat", "Livres & papeterie"],
    "NE": ["Alimentation & épicerie", "Vêtements & mode", "Maison & décoration", "Sport & loisirs"],
    "FR": ["Livres & papeterie", "Électronique & gadgets", "Vêtements & mode", "Beauté & soins"],
}

ADJECTIFS = {
    "Vêtements & mode": ["élégante", "traditionnelle", "moderne", "confortable", "tendance"],
    "Chaussures & accessoires": ["cuir", "tissé", "artisanal", "résistant", "confortable"],
    "Beauté & soins": ["naturel", "bio", "apaisant", "hydratant", "purifiant"],
    "Bijoux & artisanat": ["fait main", "unique", "précieux", "original", "traditionnel"],
    "Maison & décoration": ["déco", "artisanale", "chaleureuse", "moderne", "rustique"],
    "Électronique & gadgets": ["intelligent", "portable", "performant", "sans fil", "compact"],
    "Alimentation & épicerie": ["local", "frais", "épicé", "savoureux", "authentique"],
    "Sport & loisirs": ["résistant", "léger", "dynamique", "ergonomique", "robuste"],
    "Livres & papeterie": ["inspirant", "pratique", "éducatif", "poétique", "informatif"],
}

MATIERES = {
    "Vêtements & mode": ["coton", "lin", "wax", "soie", "denim"],
    "Chaussures & accessoires": ["cuir", "caoutchouc", "tissu", "tricot", "similicuir"],
    "Beauté & soins": ["karité", "baobab", "hibiscus", "argan", "aloe vera"],
    "Bijoux & artisanat": ["bronze", "or", "argent", "perles", "bois"],
    "Maison & décoration": ["bois", "rotin", "céramique", "textile", "métal"],
    "Électronique & gadgets": ["plastique", "métal", "verre", "silicone", "aluminium"],
    "Alimentation & épicerie": ["céréales", "épices", "fruits", "légumes", "produits locaux"],
    "Sport & loisirs": ["néoprène", "polyester", "caoutchouc", "acier", "nylon"],
    "Livres & papeterie": ["papier", "carton", "cuir", "tissu", "bambou"],
}

MARQUES_PAR_PAYS = {
    "BJ": ["Sèmè City", "Ouidah Création", "Cotonou Mode", "Ganvié Artisanat", "Porto-Novo Style"],
    "CI": ["Abidjan Design", "Yamoussoukro Déco", "San Pedro Beauté", "Bouaké Mode", "Grand-Bassam Art"],
    "SN": ["Dakar Chic", "Saint-Louis Création", "Thiès Textile", "Kaolack Beauté", "Ziguinchor Mode"],
    "TG": ["Lomé Style", "Kpalimé Artisanat", "Sokodé Déco", "Atakpamé Mode", "Tsévié Création"],
    "GH": ["Accra Mode", "Kumasi Art", "Takoradi Design", "Cape Coast Beauté", "Tamale Création"],
    "NG": ["Lagos Fashion", "Abuja Design", "Port Harcourt Style", "Kano Artisanat", "Ibadan Mode"],
    "CM": ["Douala Création", "Yaoundé Mode", "Bamenda Art", "Garoua Déco", "Ngaoundéré Style"],
    "BF": ["Ouagadougou Mode", "Bobo-Dioulasso Art", "Koudougou Création", "Ouahigouya Déco", "Tenkodogo Style"],
    "ML": ["Bamako Mode", "Ségou Création", "Mopti Artisanat", "Gao Design", "Tombouctou Style"],
    "NE": ["Niamey Mode", "Zinder Création", "Maradi Art", "Tahoua Déco", "Diffa Style"],
    "FR": ["Paris Création", "Lyon Mode", "Marseille Design", "Toulouse Art", "Bordeaux Beauté"],
}


def creer_nom_produit(categorie, pays_code, index):
    pays = COUNTRY_NAMES.get(pays_code, pays_code)
    adjectif = random.choice(ADJECTIFS.get(categorie, ["qualité"]))
    matiere = random.choice(MATIERES.get(categorie, ["local"]))
    marque = random.choice(MARQUES_PAR_PAYS.get(pays_code, ["Artisan Local"]))
    return f"{marque} - {adjectif} {categorie.lower()} {matiere} ({pays}) #{index + 1}"


def creer_description(categorie, pays_code, nom):
    pays = COUNTRY_NAMES.get(pays_code, pays_code)
    adjectif = random.choice(ADJECTIFS.get(categorie, ["authentique"]))
    return (
        f"{nom} est un produit {adjectif} provenant du {pays}. Conçu avec savoir-faire local et "
        f"matériaux de qualité, cet article incarne l'esprit de la catégorie {categorie.lower()}. "
        f"Parfait pour le quotidien ou pour offrir, il allie tradition et modernité avec élégance."
    )


class Command(BaseCommand):
    help = "Génère un catalogue synthétique local sans API externe."

    def add_arguments(self, parser):
        parser.add_argument(
            "--total",
            type=int,
            default=500,
            help="Nombre de produits à générer (défaut: 500).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Supprime les produits existants avant de générer.",
        )

    def handle(self, *args, **options):
        total = options["total"]
        force = options["force"]

        if force:
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write("Anciennes données supprimées.")

        # Créer les catégories
        categories = {}
        for cat_name in CATEGORY_QUOTAS:
            cat, _ = Category.objects.get_or_create(
                slug=slugify(cat_name),
                defaults={
                    "name": cat_name,
                    "description": f"Produits de la catégorie {cat_name}.",
                },
            )
            categories[cat_name] = cat

        # Quotas restants
        category_remaining = {}
        country_remaining = {}
        for cat, target in CATEGORY_QUOTAS.items():
            existing = Product.objects.filter(category__name=cat).count()
            category_remaining[cat] = max(target - existing, 0)
        for country, target in COUNTRY_QUOTAS.items():
            existing = Product.objects.filter(country_code=country).count()
            country_remaining[country] = max(target - existing, 0)

        available = sum(category_remaining.values())
        if available == 0:
            self.stdout.write(self.style.SUCCESS("Tous les quotas sont déjà atteints."))
            return

        total = min(total, available)
        self.stdout.write(f"{total} produit(s) à générer.")

        # Plan de génération (respecte catégorie + pays)
        plan = []
        categories_rem = dict(category_remaining)
        countries_rem = dict(country_remaining)

        while sum(countries_rem.values()) > 0 and len(plan) < total:
            possible = []
            for country, qty_c in countries_rem.items():
                if qty_c <= 0:
                    continue
                prefs = COUNTRY_CATEGORY_PREFERENCES[country]
                for cat, qty_cat in categories_rem.items():
                    if qty_cat <= 0:
                        continue
                    score = (len(prefs) - prefs.index(cat)) if cat in prefs else 0
                    possible.append((score, country, cat))
            if not possible:
                break
            best = max(p[0] for p in possible)
            best_pairs = [p for p in possible if p[0] == best]
            _, country, cat = random.choice(best_pairs)
            plan.append({"category": cat, "country_code": country})
            countries_rem[country] -= 1
            categories_rem[cat] -= 1

        random.shuffle(plan)
        plan = plan[:total]

        created = 0
        existing_names = set(Product.objects.values_list("name", flat=True))

        for i, item in enumerate(plan):
            cat_name = item["category"]
            country = item["country_code"]
            nom = creer_nom_produit(cat_name, country, i)
            if nom in existing_names:
                nom = f"{nom} bis"
            desc = creer_description(cat_name, country, nom)
            prix = Decimal(random.randint(2000, 150000))
            marque = random.choice(MARQUES_PAR_PAYS.get(country, ["Artisan"]))

            Product.objects.create(
                name=nom,
                description=desc,
                category=categories[cat_name],
                brand=marque,
                price=prix,
                currency="XOF",
                country_code=country,
                is_active=True,
            )
            existing_names.add(nom)
            created += 1

        self.stdout.write(self.style.SUCCESS(f"{created} produit(s) créé(s)."))
        self.stdout.write(f"Total actuel : {Product.objects.count()}/500")
