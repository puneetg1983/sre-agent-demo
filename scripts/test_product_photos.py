import base64
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from build_catalog import build_catalog

ROOT = Path(__file__).resolve().parents[1]


class ProductPhotoTests(unittest.TestCase):
    def test_expanded_catalog_is_deterministic_and_preserves_original_prices(self):
        products = json.loads((ROOT / "app" / "src" / "product-service" / "catalog.json").read_text())
        self.assertEqual(build_catalog(products), products)
        self.assertEqual([p["id"] for p in products], list(range(1, 211)))
        self.assertEqual([p["price"] for p in products[:10]],
                         [10, 89.99, 8.99, 49.99, 29.99, 299.99, 24.99, 59.99, 79.99, 34.99])
        self.assertTrue(all("Illustrative product-family photo" in p["description"]
                            for p in products[10:]))

    def test_catalog_assets_embed_real_jpegs_with_license_metadata(self):
        products = json.loads((ROOT / "app" / "src" / "product-service" / "catalog.json").read_text())
        self.assertEqual(len(products), 210)
        self.assertEqual(len({p["id"] for p in products}), 210)
        self.assertEqual(len({p["name"] for p in products}), 210)
        self.assertEqual(len({p["category"] for p in products}), 8)
        self.assertTrue(all(p["category"] and p["price"] > 0 for p in products))
        names = sorted({p["image"].removeprefix("/") for p in products})
        self.assertEqual(len(names), 10)
        front = ROOT / "app" / "src" / "store-front" / "public"
        admin = ROOT / "app" / "src" / "store-admin" / "public"
        credits = (front / "image-credits.txt").read_text(encoding="utf-8")
        self.assertEqual((front / "image-credits.txt").read_bytes(),
                         (admin / "image-credits.txt").read_bytes())
        namespace = "{http://www.w3.org/2000/svg}"
        for name in names:
            with self.subTest(asset=name):
                self.assertEqual((front / name).read_bytes(), (admin / name).read_bytes())
                svg = ET.parse(front / name).getroot()
                image = svg.find(namespace + "image")
                self.assertIsNotNone(image)
                uri = image.attrib["href"]
                self.assertTrue(uri.startswith("data:image/jpeg;base64,"))
                jpeg = base64.b64decode(uri.split(",", 1)[1], validate=True)
                self.assertTrue(jpeg.startswith(b"\xff\xd8") and jpeg.endswith(b"\xff\xd9"))
                metadata = svg.find(namespace + "metadata").text
                self.assertIn("Author:", metadata)
                self.assertIn("creativecommons.org/", metadata)
                self.assertIn("https://commons.wikimedia.org/", metadata)
                self.assertIn(name, credits)


if __name__ == "__main__":
    unittest.main()
