"""Günün eseri -> pixel art.

Met Museum Open Access'ten public-domain bir eser seçer (her gün aynı gün = aynı eser),
pixel art'a çevirir, altın çerçeve ekler ve docs/ altına yazar (GitHub Pages için).

Kullanım:
  python pixel_art_of_the_day.py                 # günün eserini çek + çevir
  python pixel_art_of_the_day.py --local foo.jpg # sadece converter'ı yerel dosyada dene
"""
import argparse, datetime as dt, hashlib, io, json, os, sys
from PIL import Image
import palette as pal

MET = "https://collectionapi.metmuseum.org/public/collection/v1"
SEARCH = "https://collectionapi.metmuseum.org/public/collection/v1.1/search"
GRID = 64          # pixel art çözünürlüğü (64x64 "gerçek" piksel)
COLORS = 16        # palet boyutu
SCALE = 8          # çıktı büyütme (64*8 = 512px)
OUT = "docs"

def downsample(img: Image.Image) -> Image.Image:
    """Ortadan kare kırpıp çerçeve içi boyuta (56x56) küçültür."""
    img = img.convert("RGB")
    w, h = img.size; s = min(w, h)
    img = img.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
    return img.resize((GRID - 8, GRID - 8), Image.BOX)           # alan ortalaması = temiz pikseller

def pixelate(small: Image.Image) -> Image.Image:
    small = small.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT,
                           dither=Image.Dither.NONE).convert("RGB")
    framed = add_frame(small)
    return framed.resize((GRID * SCALE, GRID * SCALE), Image.NEAREST)

def add_frame(art: Image.Image) -> Image.Image:
    """4px'lik pixel altın müze çerçevesi."""
    gold = [(92, 60, 20), (200, 150, 50), (245, 210, 110), (160, 110, 35)]
    canvas = Image.new("RGB", (GRID, GRID), gold[0])
    px = canvas.load()
    for i, col in enumerate(gold):
        for x in range(i, GRID - i):
            for y in (i, GRID - 1 - i):
                px[x, y] = col
        for y in range(i, GRID - i):
            for x in (i, GRID - 1 - i):
                px[x, y] = col
    canvas.paste(art, (4, 4))
    return canvas

UA = {"User-Agent": "pixel-museum (+https://github.com)"}

def http_get(url, timeout=20):
    import requests
    r = requests.get(url, timeout=timeout, headers=UA)
    r.raise_for_status()
    return r

def get_json(url):
    return http_get(url).json()

def search(offset: int, limit: int) -> dict:
    # v1/search 2026-10-01'de kaldırıldı; v1.1 sayfalı: {"total": N, "objectIDs": [...]}
    return get_json(f"{SEARCH}?hasImages=true&isHighlight=true&q=painting&offset={offset}&limit={limit}")

def pick_artwork(day: dt.date):
    total = search(0, 1).get("total") or 0
    if not total:
        raise RuntimeError("Met araması boş döndü")
    seed = int(hashlib.sha256(day.isoformat().encode()).hexdigest(), 16)
    for k in range(40):  # uygun olanı bulana kadar dene
        ids = search((seed + k * 7919) % total, 1).get("objectIDs") or []
        if not ids:
            continue
        obj = get_json(f"{MET}/objects/{ids[0]}")
        is_painting = "painting" in (obj.get("classification") or "").lower()
        if obj.get("isPublicDomain") and obj.get("primaryImageSmall") and is_painting:
            return obj
    raise RuntimeError("Uygun eser bulunamadı")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local")
    ap.add_argument("--base-url", default=os.environ.get("PAGES_BASE_URL", ""))
    a = ap.parse_args()
    day = dt.date.today()
    os.makedirs(f"{OUT}/art", exist_ok=True)

    if a.local:
        meta = {"title": os.path.basename(a.local), "artist": "local", "date": ""}
        src = Image.open(a.local)
    else:
        obj = pick_artwork(day)
        meta = {"title": obj["title"], "artist": obj.get("artistDisplayName") or "Unknown",
                "date": obj.get("objectDate", ""), "source": obj.get("objectURL", "")}
        src = Image.open(io.BytesIO(http_get(obj["primaryImageSmall"], timeout=30).content))

    fname = f"art/{day.isoformat()}.png"          # tarihli isim = Discord cache'ini atlatır
    small = downsample(src)
    pixelate(small).save(f"{OUT}/{fname}")
    meta["image_url"] = f"{a.base_url.rstrip('/')}/{fname}" if a.base_url else fname
    meta["caption"] = f"{meta['artist']} — {meta['title']}" + (f" ({meta['date']})" if meta["date"] else "")
    meta.update(write_palette(small, day, meta["caption"]))
    write_json(f"{OUT}/today.json", meta)
    if not a.local:                               # yerel denemeler arşive girmez
        update_archive(day, fname, meta)
    print(json.dumps(meta, ensure_ascii=False, indent=2))

def write_palette(small: Image.Image, day: dt.date, caption: str) -> dict:
    """Günün paletini docs/palettes/ altına yazar; today.json'a eklenecek alanları döner."""
    colors = pal.extract_palette(small)
    stem = f"palettes/{day.isoformat()}"
    pal.write_palette_files(colors, f"{OUT}/{stem}", f"Pixel Museum {day.isoformat()}: {caption}")
    return {"palette": pal.to_hex(colors), "palette_file": stem}

def update_archive(day: dt.date, fname: str, meta: dict) -> None:
    path = f"{OUT}/archive.json"
    try:
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
    except FileNotFoundError:
        entries = []
    keys = ("title", "artist", "date", "source", "caption", "palette", "palette_file")
    entry = {"day": day.isoformat(), "image": fname, **{k: meta.get(k, "") for k in keys}}
    write_json(path, pal.upsert_archive(entries, entry, key="day"))

def write_json(path: str, data: dict | list) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

if __name__ == "__main__":
    main()
