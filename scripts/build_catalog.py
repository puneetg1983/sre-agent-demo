import argparse
from decimal import Decimal
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "app" / "src" / "product-service" / "catalog.json"

# Each SKU uses its family's licensed photograph; preserve the original ten IDs.
FAMILIES = [
    ("Fitness & Strength", ["Mini Loop", "Power Loop", "Fabric Hip", "Tube Handle", "Assisted Pull-Up"],
     ["Light", "Medium", "Heavy", "Extra Heavy"]),
    ("Tennis", ["Court Control", "Baseline Power", "Club Precision", "Junior Rally", "Tour Balance"],
     ["Grip 0", "Grip 1", "Grip 2", "Grip 3"]),
    ("Tennis", ["All Court", "Extra Duty", "Clay Court", "Training Pressureless", "Junior Low Compression"],
     ["3-Ball Pack", "6-Ball Pack", "12-Ball Pack", "24-Ball Pack"]),
    ("Pickleball", ["Court Control", "Power Drive", "All-Round", "Club Rally", "Widebody"],
     ["Compact Grip", "Standard Grip", "Extended Grip", "Cushioned Grip"]),
    ("Table Tennis", ["Club Control", "Spin Trainer", "Defensive Play", "Match Attack", "Family Rally"],
     ["Single Paddle", "Two-Paddle Set", "Four-Paddle Set", "Training Bundle"]),
    ("Winter Sports", ["All-Mountain", "Frontside Carver", "Freeride", "Touring", "Beginner Cruiser"],
     ["150 cm", "160 cm", "170 cm", "180 cm"]),
    ("Yoga & Recovery", ["Studio Grip", "Travel Fold", "Cork Balance", "Everyday Flow", "Comfort Stretch"],
     ["3 mm", "5 mm", "6 mm", "8 mm"]),
    ("Fitness & Strength", ["2 kg Pair", "4 kg Pair", "6 kg Pair", "8 kg Pair", "10 kg Pair"],
     ["Rubber Grip", "Vinyl Finish", "Neoprene Finish", "Textured Grip"]),
    ("Running", ["Daily Trainer", "Road Cushion", "Tempo Runner", "Trail Grip", "Recovery Walk"],
     ["US 7", "US 8", "US 9", "US 10"]),
    ("Bags & Gear", ["Compact 20 L", "Club 30 L", "Training 40 L", "Weekend 50 L", "Team 60 L"],
     ["Black", "Navy", "Red", "Grey"]),
]


def build_catalog(baseline):
    originals = sorted((dict(p) for p in baseline if 1 <= p["id"] <= 10), key=lambda p: p["id"])
    if [p["id"] for p in originals] != list(range(1, 11)):
        raise ValueError("The baseline must contain each original product ID 1 through 10 exactly once")
    products = []
    for product, (category, _, _) in zip(originals, FAMILIES, strict=True):
        product["category"] = category
        products.append(product)
    for product, (category, models, options) in zip(originals, FAMILIES, strict=True):
        for model_index, model in enumerate(models):
            for option_index, option in enumerate(options):
                price = Decimal(str(product["price"])) * (
                    Decimal("0.8") + Decimal(model_index) * Decimal("0.15")
                    + Decimal(option_index) * Decimal("0.05")
                )
                products.append({
                    "id": len(products) + 1,
                    "name": f'{product["name"]} - {model}, {option}',
                    "price": float(price.quantize(Decimal("0.01"))),
                    "description": (
                        f'{product["description"]} {model} edition, {option.lower()}. '
                        "Illustrative product-family photo; finishes and quantities may vary."
                    ),
                    "image": product["image"],
                    "category": category,
                })
    return products


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rebuild the deterministic 210-SKU demo catalog")
    parser.add_argument("--baseline", type=Path, default=CATALOG)
    args = parser.parse_args()
    products = build_catalog(json.loads(args.baseline.read_text(encoding="utf-8")))
    CATALOG.write_text(json.dumps(products, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(products)} products in {len({p['category'] for p in products})} categories")
