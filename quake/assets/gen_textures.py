#!/usr/bin/env python3
"""Genera texturas del mapa (TGA), carteles de compra, iconos tactiles y el WAD2
que usa el compilador de mapas (solo para conocer tamanos; el motor usa los TGA)."""
import math, os, random, struct, sys

FONT = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#", "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".####|#....|#....|#....|#....|#....|.####", "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####", "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".####|#....|#....|#.###|#...#|#...#|.####", "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": "#####|..#..|..#..|..#..|..#..|..#..|#####", "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    "L": "#....|#....|#....|#....|#....|#....|#####", "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#", "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    "P": "####.|#...#|#...#|####.|#....|#....|#....", "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.", "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.", "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####", "3": "####.|....#|....#|.###.|....#|....#|####.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.", "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": ".###.|#....|#....|####.|#...#|#...#|.###.", "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.", "9": ".###.|#...#|#...#|.####|....#|....#|.###.",
    "-": ".....|.....|.....|#####|.....|.....|.....", "$": "..#..|.####|#.#..|.###.|..#.#|####.|..#..",
}


class Img:
    def __init__(self, w, h, fill=(0, 0, 0, 255)):
        self.w, self.h = w, h
        fill = tuple(fill) + ((255,) if len(fill) == 3 else ())
        self.p = [list(fill) for _ in range(w * h)]

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y * self.w + x] = list(c) if len(c) == 4 else list(c) + [255]

    def get(self, x, y):
        return self.p[(y % self.h) * self.w + (x % self.w)]

    def rect(self, x0, y0, x1, y1, c):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.set(x, y, c)

    def text(self, x, y, s, scale, c):
        for ch in s:
            g = FONT.get(ch)
            if g:
                for ry, row in enumerate(g.split("|")):
                    for rx, v in enumerate(row):
                        if v == "#":
                            self.rect(x + rx * scale, y + ry * scale, x + (rx + 1) * scale, y + (ry + 1) * scale, c)
            x += 6 * scale

    def save_tga(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, self.w, self.h, 32, 0x28)
        with open(path, "wb") as f:
            f.write(hdr)
            f.write(b"".join(bytes((c[2], c[1], c[0], c[3])) for c in self.p))


def clamp(v):
    return max(0, min(255, int(v)))


def shade(c, k):
    return (clamp(c[0] * k), clamp(c[1] * k), clamp(c[2] * k))


def grain(img, rng, amount):
    for i, p in enumerate(img.p):
        n = rng.uniform(-amount, amount)
        p[0] = clamp(p[0] + n); p[1] = clamp(p[1] + n); p[2] = clamp(p[2] + n)


def blobs(img, rng, count, dark, rmin, rmax):
    for _ in range(count):
        cx, cy, r = rng.randrange(img.w), rng.randrange(img.h), rng.uniform(rmin, rmax)
        for y in range(int(cy - r), int(cy + r) + 1):
            for x in range(int(cx - r), int(cx + r) + 1):
                d = math.hypot(x - cx, y - cy)
                if d < r:
                    k = 1 - dark * (1 - d / r)
                    p = img.get(x, y)
                    p[0], p[1], p[2] = clamp(p[0] * k), clamp(p[1] * k), clamp(p[2] * k)


def tex_floor(rng):
    im = Img(256, 256)
    for ty in range(2):
        for tx in range(2):
            base = rng.uniform(0.85, 1.1)
            im.rect(tx * 128, ty * 128, tx * 128 + 128, ty * 128 + 128, shade((112, 112, 116), base))
    grain(im, rng, 9)
    blobs(im, rng, 14, 0.35, 8, 28)
    for k in range(0, 256, 128):
        im.rect(k, 0, k + 3, 256, (38, 38, 42)); im.rect(0, k, 256, k + 3, (38, 38, 42))
        im.rect(k + 3, 0, k + 4, 256, (150, 150, 154)); im.rect(0, k + 3, 256, k + 4, (150, 150, 154))
    return im


def tex_wall(rng):
    im = Img(256, 256, (60, 56, 54))
    palette = [(122, 84, 66), (110, 76, 60), (132, 98, 78), (98, 80, 70), (118, 104, 92)]
    for row in range(4):
        off = 0 if row % 2 == 0 else 64
        for col in range(-1, 3):
            x0, y0 = col * 128 + off, row * 64
            c = rng.choice(palette)
            im.rect(x0 + 4, y0 + 4, x0 + 128, y0 + 64, shade(c, rng.uniform(0.85, 1.1)))
    grain(im, rng, 12)
    blobs(im, rng, 10, 0.5, 10, 36)
    return im


def tex_ceil(rng):
    im = Img(256, 256, (58, 60, 64))
    grain(im, rng, 7)
    for k in (0, 128):
        im.rect(k, 0, k + 4, 256, (28, 28, 32)); im.rect(0, k, 256, k + 4, (28, 28, 32))
    for bx in (16, 112, 144, 240):
        for by in (16, 112, 144, 240):
            im.rect(bx, by, bx + 6, by + 6, (95, 95, 100))
    return im


def tex_metal(rng):
    im = Img(256, 256)
    for x in range(256):
        k = rng.uniform(0.9, 1.1)
        for y in range(256):
            im.set(x, y, shade((92, 98, 104), k))
    grain(im, rng, 8)
    for k in (0, 252):
        im.rect(k, 0, k + 4, 256, (40, 44, 48)); im.rect(0, k, 256, k + 4, (40, 44, 48))
    im.rect(124, 0, 132, 256, (60, 64, 70))
    for y in (24, 232):
        for x in (24, 232):
            im.rect(x, y, x + 8, y + 8, (140, 146, 150))
    return im


def tex_crate(rng):
    im = Img(256, 256, (120, 84, 46))
    for row in range(4):
        im.rect(0, row * 64, 256, row * 64 + 3, (60, 38, 20))
        im.rect(0, row * 64 + 3, 256, row * 64 + 5, (150, 112, 70))
    for i in range(0, 256 * 8):
        pass
    for y in range(256):
        k = 1 + 0.07 * math.sin(y * 0.5 + (y // 64) * 3)
        for x in range(256):
            p = im.get(x, y)
            p[0], p[1], p[2] = clamp(p[0] * k), clamp(p[1] * k), clamp(p[2] * k)
    grain(im, rng, 10)
    im.rect(0, 0, 256, 16, (82, 54, 28)); im.rect(0, 240, 256, 256, (82, 54, 28))
    im.rect(0, 0, 16, 256, (82, 54, 28)); im.rect(240, 0, 256, 256, (82, 54, 28))
    for i in range(240):
        for w in range(-8, 8):
            im.set(8 + i + w, 8 + i, (88, 58, 30))
    return im


def tex_hazard(rng):
    im = Img(256, 256)
    for y in range(256):
        for x in range(256):
            im.set(x, y, (225, 180, 20) if ((x + y) // 32) % 2 == 0 else (28, 28, 28))
    grain(im, rng, 8)
    return im


PLATES = {
    "zm_buy_pistol":  ("M1911", "500", (210, 210, 210), "pistol"),
    "zm_buy_smg":     ("KUDA SMG", "1000", (255, 190, 40), "smg"),
    "zm_buy_shotgun": ("TRENCH GUN", "1500", (230, 90, 60), "shotgun"),
    "zm_buy_rifle":   ("G-43 RIFLE", "2000", (90, 190, 255), "rifle"),
    "zm_buy_jugger":  ("JUGGER-NOG", "2500", (220, 40, 40), "perk"),
}


def tex_plate(name, rng):
    title, price, col, kind = PLATES[name]
    im = Img(256, 256, (26, 26, 30))
    grain(im, rng, 5)
    im.rect(0, 0, 256, 14, col); im.rect(0, 242, 256, 256, col)
    im.rect(0, 0, 14, 256, col); im.rect(242, 0, 256, 256, col)
    im.text(128 - len("BUY") * 6 * 3 // 2 + 3, 26, "BUY", 3, col)
    # silueta del arma
    ink = (210, 210, 214)
    if kind == "pistol":
        im.rect(70, 100, 190, 122, ink); im.rect(70, 122, 100, 170, ink); im.rect(190, 104, 200, 116, ink)
    elif kind == "smg":
        im.rect(50, 100, 200, 120, ink); im.rect(200, 106, 222, 114, ink); im.rect(110, 120, 126, 168, ink); im.rect(60, 120, 80, 150, ink)
    elif kind == "shotgun":
        im.rect(30, 108, 226, 120, ink); im.rect(30, 120, 140, 130, (150, 100, 60)); im.rect(70, 124, 110, 150, (150, 100, 60))
    elif kind == "perk":
        im.rect(100, 90, 156, 160, (190, 30, 30)); im.rect(108, 80, 148, 90, ink); im.rect(112, 110, 144, 140, (240, 240, 240))
    else:
        im.rect(30, 108, 130, 124, (150, 100, 60)); im.rect(130, 104, 226, 118, ink); im.rect(100, 100, 160, 108, ink)
    ts = 4 if len(title) <= 8 else 3
    tw = len(title) * 6 * ts - ts
    im.text(128 - tw // 2, 168 + (4 if ts == 3 else 0), title, ts, (240, 240, 240))
    pw = (len(price) + 1) * 6 * 5 - 5
    im.text(128 - pw // 2, 208 - 4, "$" + price, 4, col)
    return im


WORLD = {"zm_floor": tex_floor, "zm_wall": tex_wall, "zm_ceil": tex_ceil, "zm_metal": tex_metal,
         "zm_crate": tex_crate, "zm_hazard": tex_hazard}


# ---------- iconos tactiles ------------------------------------------------------
def smooth(d, edge, soft=1.2):
    return max(0.0, min(1.0, (edge - d) / soft + 0.5))


def circle_icon(size, ring, fill, glyph):
    im = Img(size, size, (0, 0, 0, 0))
    c, r = size / 2 - 0.5, size / 2 - 2
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c)
            a_fill = smooth(d, r)
            a_ring = smooth(abs(d - (r - 2)), 2.0)
            col = fill if a_ring < 0.5 else ring
            a = max(a_fill * col[3] / 255.0, a_ring * ring[3] / 255.0)
            im.set(x, y, (col[0], col[1], col[2], clamp(a * 255)))
    glyph(im, size)
    return im


def g_fire(im, s):
    c = s // 2
    for i in range(-14, 15):
        for w in (-1, 0, 1):
            im.set(c + i, c + w, (255, 255, 255, 235)); im.set(c + w, c + i, (255, 255, 255, 235))
    for a in range(0, 360, 4):
        x, y = c + 9 * math.cos(math.radians(a)), c + 9 * math.sin(math.radians(a))
        im.set(int(x), int(y), (255, 255, 255, 235))


def g_reload(im, s):
    c = s // 2
    for a in range(40, 320, 2):
        for rr in (10, 11, 12):
            x, y = c + rr * math.cos(math.radians(a)), c + rr * math.sin(math.radians(a))
            im.set(int(x), int(y), (255, 255, 255, 240))
    for i in range(7):
        for j in range(-i, i + 1):
            im.set(c + 12 + j, c - 3 + i, (255, 255, 255, 240))


def g_buy(im, s):
    im.text(s // 2 - 8, s // 2 - 10, "$", 3, (255, 235, 120, 255))


def g_swap(im, s):
    c = s // 2
    for i in range(7):
        for j in range(-i, i + 1):
            im.set(c - 14 + i, c - 7 + j, (255, 255, 255, 240)); im.set(c + 14 - i, c + 7 + j, (255, 255, 255, 240))
    im.rect(c - 8, c - 8, c + 12, c - 5, (255, 255, 255, 240)); im.rect(c - 12, c + 5, c + 8, c + 8, (255, 255, 255, 240))


def g_jump(im, s):
    c = s // 2
    for i in range(12):
        for j in range(-i, i + 1):
            im.set(c + j, c - 12 + i, (255, 255, 255, 240))
    im.rect(c - 3, c, c + 4, c + 12, (255, 255, 255, 240))


def stick_icon():
    im = Img(128, 128, (0, 0, 0, 0))
    c = 63.5
    for y in range(128):
        for x in range(128):
            d = math.hypot(x - c, y - c)
            a = max(smooth(abs(d - 58), 2.5) * 0.55, smooth(d, 22) * 0.25 + smooth(abs(d - 22), 2.0) * 0.4)
            im.set(x, y, (255, 255, 255, clamp(a * 255)))
    return im


# ---------- WAD2 -------------------------------------------------------------------
def write_wad(path, names):
    lumps = []
    for n in names:
        w = h = 64
        idx = 8
        pix = bytes([idx]) * (w * h)
        mips = [pix, bytes([idx]) * (32 * 32), bytes([idx]) * (16 * 16), bytes([idx]) * (8 * 8)]
        hdr = struct.pack("<16sIIIIII", n.encode(), w, h, 40, 40 + w * h, 40 + w * h + 32 * 32, 40 + w * h + 32 * 32 + 16 * 16)
        lumps.append((n, hdr + b"".join(mips)))
    data, entries, pos = b"", [], 12
    for n, blob in lumps:
        entries.append(struct.pack("<iiibbh16s", pos, len(blob), len(blob), 0x44, 0, 0, n.encode()))
        data += blob
        pos += len(blob)
    with open(path, "wb") as f:
        f.write(b"WAD2" + struct.pack("<ii", len(lumps), pos) + data + b"".join(entries))


def main(out):
    rng = random.Random(11)
    names = []
    for n, fn in WORLD.items():
        fn(rng).save_tga(os.path.join(out, "textures", n + ".tga")); names.append(n)
    for n in PLATES:
        tex_plate(n, rng).save_tga(os.path.join(out, "textures", n + ".tga")); names.append(n)
    os.makedirs(os.path.join(out, "wad"), exist_ok=True)
    write_wad(os.path.join(out, "wad", "zm.wad"), names)

    ring, fill = (255, 255, 255, 170), (30, 30, 30, 120)
    circle_icon(64, ring, (170, 30, 30, 140), g_fire).save_tga(os.path.join(out, "gfx", "touch_fire.tga"))
    circle_icon(64, ring, fill, g_reload).save_tga(os.path.join(out, "gfx", "touch_reload.tga"))
    circle_icon(64, ring, (140, 110, 20, 140), g_buy).save_tga(os.path.join(out, "gfx", "touch_buy.tga"))
    circle_icon(64, ring, fill, g_swap).save_tga(os.path.join(out, "gfx", "touch_swap.tga"))
    circle_icon(64, ring, fill, g_jump).save_tga(os.path.join(out, "gfx", "touch_jump.tga"))
    stick_icon().save_tga(os.path.join(out, "gfx", "touch_stick.tga"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build/pak")
