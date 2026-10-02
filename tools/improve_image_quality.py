from pathlib import Path
from PIL import Image, ImageFilter
import hashlib, json, re, shutil

root = Path(__file__).resolve().parents[1]
assets = root / "assets"
page = root / "index.html"
text = page.read_text(encoding="utf-8")
sources = sorted(p for p in assets.glob("*.webp") if "-hq" not in p.stem)
rows = []
for source in sources:
    target = source.with_name(source.stem + "-hq.webp")
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    with Image.open(source) as image:
        original_size = image.size
        enhanced = image.convert("RGB").resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
        enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55, threshold=3))
        enhanced.save(target, "WEBP", quality=88, method=6)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    with Image.open(target) as check:
        assert check.size == (original_size[0] * 2, original_size[1] * 2)
        check.verify()
    rows.append({"original": source.name, "enhanced": target.name, "original_size": original_size,
                 "enhanced_size": [original_size[0] * 2, original_size[1] * 2],
                 "original_bytes": source.stat().st_size, "enhanced_bytes": target.stat().st_size,
                 "original_sha256": original_hash})
    text = text.replace("assets/" + source.name, "assets/" + target.name)

# Cards retain the smaller original on standard-density screens.
for source in sources:
    if source.stem.startswith("w-"):
        target = source.with_name(source.stem + "-hq.webp")
        pattern = ('src="assets/' + re.escape(source.stem)
                   + '(?:-hq)?[.]webp"(?: srcset="[^"]*")?')
        replacement = ('src="assets/' + source.name + '" srcset="assets/' + source.name
                       + ' 1x, assets/' + target.name + ' 2x"')
        text = re.sub(pattern, lambda match: replacement, text)

backup = root / ".image-quality-backup"
backup.mkdir(exist_ok=True)
if not (backup / "index.html").exists():
    shutil.copy2(page, backup / "index.html")
page.write_text(text, encoding="utf-8", newline="")
report = {"method": "Lanczos 2x interpolation, mild unsharp mask, WebP quality 88",
          "note": "No generative AI. Original pixels, faces and composition preserved. Interpolation does not recover missing source detail.",
          "images": rows,
          "original_total_bytes": sum(r["original_bytes"] for r in rows),
          "enhanced_total_bytes": sum(r["enhanced_bytes"] for r in rows)}
(root / "image-quality-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
refs = set(re.findall(r"assets/[A-Za-z0-9_-]+[.](?:webp|png)", text))
for ref in refs:
    assert (root / ref).is_file(), ref
print(json.dumps({"images":len(rows), "original_bytes":report["original_total_bytes"],
                 "enhanced_bytes":report["enhanced_total_bytes"], "backup":str(backup)}, ensure_ascii=False))
