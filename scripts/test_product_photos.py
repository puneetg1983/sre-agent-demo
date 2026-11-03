import base64
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class ProductPhotoTests(unittest.TestCase):
    def test_catalog_assets_embed_real_jpegs_with_license_metadata(self):
        model = (ROOT / "app" / "src" / "product-service" / "src" / "models.rs").read_text()
        names = re.findall(r'image: "/([^"]+\.svg)"', model)
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
