import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
import palette as P


def solid_blocks(blocks, w=56):
    """blocks: list of (color, row_count) stacked vertically."""
    h = sum(n for _, n in blocks)
    img = Image.new("RGB", (w, h))
    y = 0
    for col, n in blocks:
        img.paste(col, (0, y, w, y + n))
        y += n
    return img


class ColorMath(unittest.TestCase):
    def test_lab_extremes(self):
        L, a, b = P.rgb_to_lab((255, 255, 255))
        self.assertAlmostEqual(L, 100, delta=0.1)
        self.assertAlmostEqual(a, 0, delta=0.1)
        self.assertAlmostEqual(b, 0, delta=0.1)
        self.assertAlmostEqual(P.rgb_to_lab((0, 0, 0))[0], 0, delta=0.01)

    def test_lab_red_reference(self):
        L, a, b = P.rgb_to_lab((255, 0, 0))  # reference: 53.24, 80.09, 67.20
        self.assertAlmostEqual(L, 53.24, delta=0.2)
        self.assertAlmostEqual(a, 80.09, delta=0.5)
        self.assertAlmostEqual(b, 67.20, delta=0.5)


class Extract(unittest.TestCase):
    def test_returns_exact_colors_when_few(self):
        cols = [(10, 10, 10), (200, 30, 30), (240, 240, 220)]
        img = solid_blocks([(c, 10) for c in cols])
        pal = P.extract_palette(img, n=8)
        self.assertEqual(sorted(pal), sorted(cols))

    def test_size_and_lightness_order(self):
        blocks = [((i * 15, (i * 37) % 256, 255 - i * 15), 3) for i in range(17)]
        pal = P.extract_palette(solid_blocks(blocks), n=8)
        self.assertEqual(len(pal), 8)
        Ls = [P.rgb_to_lab(c)[0] for c in pal]
        self.assertEqual(Ls, sorted(Ls))

    def test_small_accent_survives(self):
        # 16 near-identical browns dominate; a few rows of red must still make it in
        browns = [((90 + i, 60 + i, 30), 6) for i in range(16)]
        img = solid_blocks(browns + [((220, 20, 30), 2)])
        pal = P.extract_palette(img, n=8)
        self.assertIn((220, 20, 30), pal)

    def test_deterministic(self):
        blocks = [((i * 13 % 256, i * 29 % 256, i * 47 % 256), 2) for i in range(28)]
        img = solid_blocks(blocks)
        self.assertEqual(P.extract_palette(img), P.extract_palette(img))


class Formats(unittest.TestCase):
    PAL = [(0, 0, 0), (255, 136, 1)]

    def test_hex(self):
        self.assertEqual(P.to_hex(self.PAL), ["000000", "ff8801"])
        self.assertEqual(P.format_hex(self.PAL), "000000\nff8801\n")

    def test_gpl(self):
        txt = P.format_gpl(self.PAL, "Pixel Museum 2026-11-26")
        lines = txt.splitlines()
        self.assertEqual(lines[0], "GIMP Palette")
        self.assertEqual(lines[1], "Name: Pixel Museum 2026-11-26")
        self.assertIn("255 136   1\tff8801", lines)

    def test_write_all(self):
        with tempfile.TemporaryDirectory() as d:
            paths = P.write_palette_files(self.PAL, os.path.join(d, "x"), "t")
            self.assertEqual(sorted(os.path.basename(p) for p in paths), ["x.gpl", "x.hex", "x.png"])
            strip = Image.open(os.path.join(d, "x.png")).convert("RGB")
            self.assertEqual(strip.size, (2, 1))
            self.assertEqual(strip.getpixel((1, 0)), (255, 136, 1))


class Archive(unittest.TestCase):
    def test_upsert_replaces_and_sorts_newest_first(self):
        old = [{"date": "2026-11-24", "title": "a"}, {"date": "2026-11-25", "title": "b"}]
        new = P.upsert_archive(old, {"date": "2026-11-25", "title": "B"})
        self.assertEqual([e["title"] for e in new], ["B", "a"])
        self.assertEqual(old[1]["title"], "b")  # input untouched
        new2 = P.upsert_archive(new, {"date": "2026-11-26", "title": "c"})
        self.assertEqual([e["date"] for e in new2], ["2026-11-26", "2026-11-25", "2026-11-24"])

    def test_custom_key(self):
        old = [{"day": "2026-11-25", "date": "1888"}]
        new = P.upsert_archive(old, {"day": "2026-11-25", "date": "1890"}, key="day")
        self.assertEqual(new, [{"day": "2026-11-25", "date": "1890"}])


if __name__ == "__main__":
    unittest.main()
