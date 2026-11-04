"""Extract the independently generated product images from reviewed asset sheets."""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHEETS = [
    ("3f2316402edbead68666e2e3739e1f26b4d55606598cca3c315766fd68a6120e",
     [0, 279, 560, 841, 1121], [0, 280, 538, 823, 1104, 1403]),
    ("4c98e4572313e0afacca8e7700562c350e783ab80c25528b59f9b3d98d8cd46a",
     [2, 256, 511, 767, 1022], [2, 307, 612, 913, 1216, 1534]),
    ("34b377a6d786b07e57e7ad9cbeb96dcbea29d2231484fb4fee6c86cde3d08c60",
     [0, 288, 560, 832, 1122], [0, 259, 508, 753, 1006, 1246]),
    ("0f950964b92264a350b1f5cca93ac42fe6a69a4efcee1b934b80df9cfa1d5fc4",
     [0, 272, 560, 848, 1122], [0, 277, 558, 840, 1122, 1402]),
    ("172d4ac8704405a56ac1e5cce6397e22c83d6ff62daa9b5714b99fb2994ca7b1",
     [0, 299, 607, 915, 1214], [0, 258, 515, 774, 1032, 1295]),
    ("ba75420f828cbbc83c2becd3a30b114432266f165289a6a8a6d02f29696bbd7e",
     [0, 279, 560, 842, 1122], [0, 279, 546, 815, 1104, 1402]),
    ("7ae46e61ec5811c112a80849b79da90dc2d204405164fac7fffdeae9c410eed7",
     [0, 255, 511, 767, 1024], [0, 305, 605, 886, 1192, 1536]),
    ("091631c25d9490e993885fcc997638b53063ef72a69356611148659958e43f90",
     [0, 283, 560, 837, 1122], [0, 279, 551, 823, 1098, 1402]),
    ("f5c0906dc6605f87663ed1d24ae80e394e0f2637969bceaf080fab3f9fdafd2f",
     [0, 255, 511, 768, 1024], [0, 305, 605, 901, 1206, 1536]),
    ("eca7ebef9ec4b88ee7d8eb30900e3261dca5b46c361a0ddd5f8d230fb8d0bf7c",
     [0, 254, 511, 768, 1024], [0, 304, 602, 898, 1211, 1536]),
]


def prepare(source_dir):
    sources = {}
    for path in source_dir.glob("*.png"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in {sheet[0] for sheet in SHEETS}:
            sources[digest] = path
    missing = {sheet[0] for sheet in SHEETS} - sources.keys()
    if missing:
        raise ValueError(f"Missing original generated asset sheets: {sorted(missing)}")
    public = [ROOT / "app" / "src" / app / "public" for app in ("store-front", "store-admin")]
    manifest = []
    for family, (digest, xs, ys) in enumerate(SHEETS):
        with Image.open(sources[digest]) as source:
            source = source.convert("RGB")
            for row in range(5):
                for column in range(4):
                    product_id = 11 + family * 20 + row * 4 + column
                    bounds = [xs[column] + 4, ys[row] + 4, xs[column + 1] - 4, ys[row + 1] - 4]
                    image = source.crop(bounds)
                    if min(image.size) < 220:
                        raise ValueError(f"Product {product_id} has an undersized image")
                    relative = Path("products") / f"product-{product_id:04}.jpg"
                    destination = public[0] / relative
                    destination.parent.mkdir(exist_ok=True)
                    image.save(destination, format="JPEG", quality=92, optimize=True, progressive=True)
                    data = destination.read_bytes()
                    for directory in public[1:]:
                        (directory / relative).parent.mkdir(exist_ok=True)
                        (directory / relative).write_bytes(data)
                    manifest.append({
                        "productId": product_id,
                        "image": "/" + relative.as_posix(),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "width": image.width,
                        "height": image.height,
                        "generationImageId": "sha256:" + digest,
                        "panel": {"row": row + 1, "column": column + 1, "bounds": bounds},
                    })
    if len({photo["sha256"] for photo in manifest}) != 200:
        raise ValueError("Repeated product photograph detected")
    output = {"origin": "AI-generated illustrative product images, created for this demo.",
              "photos": manifest}
    (ROOT / "app" / "src" / "product-service" / "photo-manifest.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8")
    marker = "\nAI-GENERATED UNIQUE PRODUCT IMAGES\n"
    original_credits = (public[0] / "image-credits.txt").read_text(encoding="utf-8").split(marker)[0]
    credits = original_credits.rstrip() + "\n" + marker + """
The 200 added products (IDs 11-210) each have a separate, distinct AI-generated
studio-style product image created for this demo. These are illustrative images,
not photographs of actual inventory; finishes, colors and quantities may vary.
They do not depict or imply endorsement by any real brand or manufacturer.
The ten original Wikimedia photographs retain their separate licenses above.
Provenance and file hashes: app/src/product-service/photo-manifest.json.
Processing: extracted individual photographs from generated asset sheets,
trimmed only grid separators, and JPEG-compressed. No photo is assigned twice.

""" + "\n".join(f'{photo["image"]} - product {photo["productId"]}' for photo in manifest) + "\n"
    for directory in public:
        (directory / "image-credits.txt").write_text(credits, encoding="utf-8")
    print(f"Prepared {len(manifest)} distinct images in both websites.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    prepare(parser.parse_args().source_dir)
