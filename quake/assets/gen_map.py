#!/usr/bin/env python3
"""Genera maps/zombies.map (formato Valve 220) para compilarlo con ericw-tools.

Arena de 1280x1280 con 4 corrales de aparicion en las esquinas, pilares, cajas,
un bloque central y 4 carteles de compra de armas en las paredes.
"""
import sys

TEX = {"floor": "zm_floor", "wall": "zm_wall", "ceil": "zm_ceil", "metal": "zm_metal", "crate": "zm_crate", "haz": "zm_hazard"}
AXES = {  # ejes de textura (u, v) segun la normal de la cara
    (0, 0, 1): ((1, 0, 0), (0, -1, 0)), (0, 0, -1): ((1, 0, 0), (0, -1, 0)),
    (1, 0, 0): ((0, 1, 0), (0, 0, -1)), (-1, 0, 0): ((0, 1, 0), (0, 0, -1)),
    (0, 1, 0): ((1, 0, 0), (0, 0, -1)), (0, -1, 0): ((1, 0, 0), (0, 0, -1)),
}
NORMALS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def add(a, b, k=1):
    return tuple(a[i] + b[i] * k for i in range(3))


def tangents(n):
    """t1, t2 tales que (t2 x t1) = n  (convencion de Quake: (p3-p1)x(p2-p1) apunta hacia fuera)."""
    axes = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    a = [t for t in axes if t[0] * n[0] + t[1] * n[1] + t[2] * n[2] == 0]
    t1, t2 = a[0], a[1]
    if cross(t2, t1) != n:
        t1, t2 = t2, t1
    assert cross(t2, t1) == n
    return t1, t2


class Brush:
    def __init__(self, mins, maxs, tex, scale=2.0, plate=None):
        self.mins, self.maxs = mins, maxs
        self.tex = tex if isinstance(tex, dict) else {"all": tex}
        self.scale = scale
        self.plate = plate   # (cara normal, offset u, offset v) para carteles

    def face_tex(self, n):
        key = {(0, 0, 1): "top", (0, 0, -1): "bottom"}.get(n, "side")
        return self.tex.get(key, self.tex.get("all", TEX["wall"]))

    def text(self):
        (x0, y0, z0), (x1, y1, z1) = self.mins, self.maxs
        assert x1 > x0 and y1 > y0 and z1 > z0, (self.mins, self.maxs)
        c = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        lines = ["{"]
        for n in NORMALS:
            px = [x1 if n[0] > 0 else x0, y1 if n[1] > 0 else y0, z1 if n[2] > 0 else z0]
            # punto del plano: esquina en la direccion de la normal (el eje de la normal fija el plano)
            p = tuple((px[i] if n[i] != 0 else (x0, y0, z0)[i]) for i in range(3))
            t1, t2 = tangents(n)
            p1, p2, p3 = p, add(p, t1, 16), add(p, t2, 16)
            nn = cross(add(p3, p1, -1), add(p2, p1, -1))
            assert nn == tuple(256 * k for k in n), (nn, n)
            assert sum((p[i] - c[i]) * n[i] for i in range(3)) > 0   # hacia fuera
            u, v = AXES[n]
            offu, offv = 0, 0
            scale = self.scale
            if self.plate and self.plate[0] == n:
                scale = 1.0
                u, v = self.plate[1], (0, 0, -1)
                offu = self.plate[2]
                offv = z1
            lines.append("( %d %d %d ) ( %d %d %d ) ( %d %d %d ) %s [ %d %d %d %g ] [ %d %d %d %g ] 0 %g %g" % (
                *p1, *p2, *p3, self.face_tex(n) if not (self.plate and self.plate[0] == n) else self.plate_tex,
                *u, offu, *v, offv, scale, scale))
        lines.append("}")
        return "\n".join(lines)


def box(x0, y0, z0, x1, y1, z1, tex, **kw):
    return Brush((x0, y0, z0), (x1, y1, z1), tex, **kw)


def build():
    R, H, T = 640, 256, 32           # radio interior, altura, grosor de pared
    W, F, C, M, K = TEX["wall"], TEX["floor"], TEX["ceil"], TEX["metal"], TEX["crate"]
    brushes = []

    # --- carcasa de la arena
    brushes.append(box(-R - T, -R - T, -T, R + T, R + T, 0, {"top": F, "all": W}))
    brushes.append(box(-R - T, -R - T, H, R + T, R + T, H + T, {"bottom": C, "all": W}))
    brushes.append(box(-R - T, R, 0, R + T, R + T, H, W))      # norte
    brushes.append(box(-R - T, -R - T, 0, R + T, -R, H, W))    # sur
    brushes.append(box(R, -R, 0, R + T, R, H, W))              # este
    brushes.append(box(-R - T, -R, 0, -R, R, H, W))            # oeste

    # --- corrales de aparicion en las 4 esquinas (huecos de 80 en cada lado)
    for sx in (1, -1):
        for sy in (1, -1):
            def mk(ax0, ay0, ax1, ay1):
                xs = sorted((ax0 * sx, ax1 * sx)); ys = sorted((ay0 * sy, ay1 * sy))
                brushes.append(box(xs[0], ys[0], 0, xs[1], ys[1], H, W))
            mk(464, 560, 480, R)      # muro vertical pegado a la pared
            mk(560, 464, R, 480)      # muro horizontal pegado a la pared

    # --- bloque central, pilares y cajas
    brushes.append(box(-128, -128, 0, 128, 128, 64, {"top": TEX["haz"], "all": M}))
    for sx in (1, -1):
        for sy in (1, -1):
            brushes.append(box(sx * 256 - 24, sy * 256 - 24, 0, sx * 256 + 24, sy * 256 + 24, H, M))
            brushes.append(box(sx * 384 - 48, sy * 384 - 48, 0, sx * 384 + 48, sy * 384 + 48, 64, K, scale=1.5))

    # --- carteles de compra (64x64, pegados a la pared, mirando al centro)
    plates = [
        ("zm_buy_smg", (0, 1), (-32, R - 8, 32, 32, R, 96), (0, -1, 0), (1, 0, 0), 32),        # norte
        ("zm_buy_shotgun", (1, 0), (R - 8, -32, 32, R, 32, 96), (-1, 0, 0), (0, -1, 0), 32),    # este
        ("zm_buy_rifle", (0, -1), (-32, -R, 32, 32, -R + 8, 96), (0, 1, 0), (-1, 0, 0), 32),    # sur
        ("zm_buy_pistol", (-1, 0), (-R, -32, 32, -R + 8, 32, 96), (1, 0, 0), (0, 1, 0), 32),    # oeste
        ("zm_buy_jugger", (0, 1), (-400, R - 8, 32, -336, R, 96), (0, -1, 0), (1, 0, 0), 32),   # norte, a un lado
        ("zm_buy_speed", (0, 1), (336, R - 56, 32, 400, R - 48, 96), (0, -1, 0), (1, 0, 0), 32),    # norte
        ("zm_buy_dtap", (-1, 0), (-R + 48, 336, 32, -R + 56, 400, 96), (1, 0, 0), (0, 1, 0), 32),   # oeste
        ("zm_buy_widow", (0, -1), (-400, -R + 48, 32, -336, -R + 56, 96), (0, 1, 0), (-1, 0, 0), 32),   # sur
        ("zm_buy_gum", (1, 0), (R - 56, -332, 32, R - 48, -268, 96), (-1, 0, 0), (0, -1, 0), 32),   # maquina de chicles (este)
    ]
    for name, d, (x0, y0, z0, x1, y1, z1), face, u, _ in plates:
        b = box(x0, y0, z0, x1, y1, z1, M)
        b.plate_tex = name
        # u de la textura: el borde izquierdo (visto desde la sala) debe valer s=0
        if u == (1, 0, 0):
            off = -x0
        elif u == (-1, 0, 0):
            off = x1
        elif u == (0, -1, 0):
            off = y1
        else:
            off = -y0
        b.plate = (face, u, off)
        brushes.append(b)

    # cuerpo de la maquina de chicles: base, soporte y cupula
    brushes.append(box(R - 56, -332, 0, R - 48, -268, 32, M))
    brushes.append(box(R - 48, -332, 0, R, -268, 96, M))
    brushes.append(box(R - 56, -332, 96, R, -268, 112, {"top": TEX["haz"], "all": M}))

    # cuerpos de las maquinas de perks (junto a la pared, detras del cartel)
    for x0, y0, x1, y1 in ((336, R - 48, 400, R), (-R, 336, -R + 48, 400), (-400, -R, -336, -R + 48)):
        brushes.append(box(x0, y0, 0, x1, y1, 96, M))
        brushes.append(box(x0, y0, 96, x1, y1, 108, {"top": TEX["haz"], "all": M}))
    for x0, y0, x1, y1 in ((336, R - 56, 400, R - 48), (-R + 48, 336, -R + 56, 400), (-400, -R + 48, -336, -R + 56)):
        brushes.append(box(x0, y0, 0, x1, y1, 32, M))      # base bajo el cartel

    ents = []
    for sx in (1, -1):
        for sy in (1, -1):
            ents.append({"classname": "info_zombie_spawn", "origin": "%d %d 4" % (sx * 590, sy * 590)})
    ents.append({"classname": "info_player_start", "origin": "0 -300 28", "angles": "0 90 0"})
    for name, wep, org in (("smg", 1, "0 596 28"), ("shotgun", 2, "596 0 28"), ("rifle", 3, "0 -596 28"), ("pistol", 0, "-596 0 28"), ("jugger", 10, "-368 596 28"), ("gum", 11, "566 -300 28"), ("dtap", 12, "-596 368 28"), ("speed", 13, "368 596 28"), ("widow", 14, "-368 -596 28")):
        ents.append({"classname": "zm_buy", "origin": org, "wep": str(wep)})
    for x in (-480, -160, 160, 480):
        for y in (-480, -160, 160, 480):
            ents.append({"classname": "light", "origin": "%d %d 224" % (x, y), "light": "300"})
    for sx in (1, -1):
        for sy in (1, -1):
            ents.append({"classname": "light", "origin": "%d %d 200" % (sx * 570, sy * 570), "light": "230"})
    return brushes, ents


def main(path):
    brushes, ents = build()
    out = ["// Zombies - arena generada por gen_map.py", "{", '"mapversion" "220"', '"classname" "worldspawn"', '"wad" "zm.wad"', '"_minlight" "38"', '"message" "Zombies"']
    for b in brushes:
        out.append(b.text())
    out.append("}")
    for e in ents:
        out.append("{")
        for k, v in e.items():
            out.append('"%s" "%s"' % (k, v))
        out.append("}")
    open(path, "w").write("\n".join(out) + "\n")
    print("brushes:", len(brushes), "entities:", len(ents))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "zombies.map")
