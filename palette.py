"""Günün paleti: bir görselden 8 renklik, pixel artist'lere uygun palet çıkarır.

Yöntem (prototipte median cut ve düz k-means'e karşı en iyi sonucu verdi):
  1. Renkler CIELAB'a çevrilir (öklid mesafesi ≈ algısal fark, ΔE76).
  2. Ağırlıklı k-means (k=16, deterministik k-means++ başlangıcı) ile aşırı kümelenir.
  3. Kümeler Ward maliyetiyle (ΔE² · nᵢnⱼ/(nᵢ+nⱼ)) 8'e birleştirilir: benzer ve küçük
     kümeler önce birleşir, küçük ama farklı vurgu renkleri (bir kırmızı pelerin) hayatta kalır.
  4. Her küme, merkezine en yakın *gerçek* piksel rengiyle temsil edilir (ortalama almak
     renkleri soldurur). Palet açıklığa (L*) göre sıralanır.

Veri ~3k piksel olduğu için saf Python yeterli (~1 sn); numpy bağımlılığı gerekmez.
"""
from __future__ import annotations

import os
import random
from collections import Counter
from typing import Iterable, Sequence

from PIL import Image

RGB = tuple[int, int, int]
Lab = tuple[float, float, float]

PALETTE_SIZE = 8
OVERCLUSTER = 16
KMEANS_ITERS = 30
SEED = 0


# ---------------------------------------------------------------- color math
def _linear(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _f(t: float) -> float:
    return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116


def rgb_to_lab(rgb: RGB) -> Lab:
    """sRGB (0-255) -> CIELAB, D65 beyaz noktası."""
    r, g, b = (_linear(float(v)) for v in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    fx, fy, fz = _f(x), _f(y), _f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _d2(a: Lab, b: Lab) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


# ---------------------------------------------------------------- clustering
class _Cluster:
    __slots__ = ("members", "weight", "center")

    def __init__(self, members: list[int], weight: int, center: Lab) -> None:
        self.members, self.weight, self.center = members, weight, center


def _init_centers(labs: Sequence[Lab], weights: Sequence[int], k: int, rnd: random.Random) -> list[Lab]:
    """Ağırlıklı k-means++."""
    first = rnd.choices(range(len(labs)), weights=weights)[0]
    centers = [labs[first]]
    dist = [_d2(p, centers[0]) for p in labs]
    while len(centers) < k:
        scores = [d * w for d, w in zip(dist, weights)]
        if not any(scores):
            break
        pick = rnd.choices(range(len(labs)), weights=scores)[0]
        centers.append(labs[pick])
        dist = [min(d, _d2(p, labs[pick])) for d, p in zip(dist, labs)]
    return centers


def _kmeans(labs: Sequence[Lab], weights: Sequence[int], k: int) -> list[_Cluster]:
    rnd = random.Random(SEED)
    centers = _init_centers(labs, weights, k, rnd)
    groups: list[list[int]] = []
    for _ in range(KMEANS_ITERS):
        groups = [[] for _ in centers]
        for i, p in enumerate(labs):
            groups[min(range(len(centers)), key=lambda j: _d2(p, centers[j]))].append(i)
        new = [_weighted_mean(g, labs, weights) if g else c for g, c in zip(groups, centers)]
        if new == centers:
            break
        centers = new
    return [_Cluster(g, sum(weights[i] for i in g), c) for g, c in zip(groups, centers) if g]


def _weighted_mean(idx: Sequence[int], labs: Sequence[Lab], weights: Sequence[int]) -> Lab:
    total = sum(weights[i] for i in idx)
    return tuple(sum(labs[i][t] * weights[i] for i in idx) / total for t in range(3))  # type: ignore[return-value]


def _merge_to(clusters: list[_Cluster], n: int, labs: Sequence[Lab], weights: Sequence[int]) -> list[_Cluster]:
    """En düşük Ward maliyetli çifti, n küme kalana kadar birleştirir."""
    cl = list(clusters)
    while len(cl) > n:
        cost, i, j = min(
            (_d2(a.center, b.center) * a.weight * b.weight / (a.weight + b.weight), i, j)
            for i, a in enumerate(cl)
            for j, b in enumerate(cl)
            if i < j
        )
        members = cl[i].members + cl[j].members
        merged = _Cluster(members, cl[i].weight + cl[j].weight, _weighted_mean(members, labs, weights))
        cl = [c for t, c in enumerate(cl) if t not in (i, j)] + [merged]
    return cl


# ---------------------------------------------------------------- public API
def extract_palette(img: Image.Image, n: int = PALETTE_SIZE) -> list[RGB]:
    """Görselden n renklik palet; açıklığa göre koyudan açığa sıralı."""
    rgb = img.convert("RGB")
    pixels = rgb.get_flattened_data() if hasattr(rgb, "get_flattened_data") else rgb.getdata()
    counts = Counter(pixels)
    colors: list[RGB] = list(counts)
    labs = [rgb_to_lab(c) for c in colors]
    if len(colors) <= n:
        reps = colors
    else:
        weights = [counts[c] for c in colors]
        clusters = _merge_to(_kmeans(labs, weights, max(n, OVERCLUSTER)), n, labs, weights)
        reps = [colors[min(c.members, key=lambda i: _d2(labs[i], c.center))] for c in clusters]
    return sorted(reps, key=lambda c: rgb_to_lab(c)[0])


def to_hex(pal: Iterable[RGB]) -> list[str]:
    return ["%02x%02x%02x" % c for c in pal]


def format_hex(pal: Sequence[RGB]) -> str:
    """Lospec .hex: satır başına bir renk, '#' yok."""
    return "".join(h + "\n" for h in to_hex(pal))


def format_gpl(pal: Sequence[RGB], name: str) -> str:
    """GIMP / Aseprite / Krita .gpl."""
    rows = ["GIMP Palette", f"Name: {name}", f"Columns: {len(pal)}", "#"]
    rows += [f"{r:3d} {g:3d} {b:3d}\t{h}" for (r, g, b), h in zip(pal, to_hex(pal))]
    return "\n".join(rows) + "\n"


def palette_strip(pal: Sequence[RGB]) -> Image.Image:
    """Renk başına 1 piksellik PNG şerit (Lospec/Aseprite içe aktarma)."""
    img = Image.new("RGB", (len(pal), 1))
    img.putdata(list(pal))
    return img


def write_palette_files(pal: Sequence[RGB], stem: str, name: str) -> list[str]:
    """stem.hex, stem.gpl, stem.png yazar; yolları döner."""
    os.makedirs(os.path.dirname(stem) or ".", exist_ok=True)
    paths = [f"{stem}.hex", f"{stem}.gpl", f"{stem}.png"]
    with open(paths[0], "w", encoding="utf-8", newline="\n") as f:
        f.write(format_hex(pal))
    with open(paths[1], "w", encoding="utf-8", newline="\n") as f:
        f.write(format_gpl(pal, name))
    palette_strip(pal).save(paths[2])
    return paths


def upsert_archive(entries: Sequence[dict], entry: dict, key: str = "date") -> list[dict]:
    """Aynı tarihli kaydı değiştirir, yeniden eskiye sıralı yeni liste döner."""
    kept = [e for e in entries if e.get(key) != entry[key]]
    return sorted(kept + [dict(entry)], key=lambda e: e[key], reverse=True)
