#!/usr/bin/env python3
"""Genera los modelos MD3 (zombie y armas en primera persona) a partir de cajas,
y sus texturas. Sin dependencias externas.

Zombie: 16 cuadros (0-7 caminar, 8-11 atacar, 12-15 morir).  Pies en z=-24.
Armas:  0 reposo, 1-3 disparo, 4-7 recarga.
"""
import math, os, random, struct, sys

# ---------------------------------------------------------------- geometria
# region de textura (u0,v0,u1,v1) en una imagen de 64x64
SKIN, SHIRT, PANTS, FACE = (1, 1, 30, 14), (1, 17, 30, 30), (1, 33, 30, 46), (33, 1, 62, 30)
METAL, WOOD, LIGHT, CLOTH = (1, 1, 14, 14), (17, 1, 30, 14), (33, 1, 46, 14), (49, 1, 62, 14)
RAGS, RIBS, BONE = (1, 49, 30, 62), (33, 33, 46, 46), (49, 33, 62, 46)   # solo zombie

# caras: indices de esquinas (0..7) y normal local
CORNERS = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
FACES = [((1, 2, 6, 5), (1, 0, 0)), ((3, 0, 4, 7), (-1, 0, 0)), ((2, 3, 7, 6), (0, 1, 0)),
         ((0, 1, 5, 4), (0, -1, 0)), ((4, 5, 6, 7), (0, 0, 1)), ((0, 3, 2, 1), (0, 0, -1))]


def rot_y(p, pivot, deg):
    """Gira el punto alrededor del eje Y (cabeceo) con el pivote dado.
    Angulo positivo = la parte alta se va hacia delante (+x)."""
    a = math.radians(deg)
    x, y, z = p[0] - pivot[0], p[1], p[2] - pivot[2]
    return (pivot[0] + x * math.cos(a) + z * math.sin(a), p[1], pivot[2] - x * math.sin(a) + z * math.cos(a))


class Box:
    def __init__(self, x0, x1, y0, y1, z0, z1, region, face_regions=None):
        self.b = (x0, x1, y0, y1, z0, z1)
        self.region = region
        self.face_regions = face_regions or {}

    def verts(self, xform):
        x0, x1, y0, y1, z0, z1 = self.b
        pts = []
        for cx, cy, cz in CORNERS:
            p = (x0 if cx < 0 else x1, y0 if cy < 0 else y1, z0 if cz < 0 else z1)
            pts.append(xform(p))
        return pts


class Mesh:
    """Lista fija de triangulos/UV; cada cuadro solo cambia las posiciones."""
    def __init__(self, boxes):
        self.boxes = boxes
        self.uv, self.tris = [], []
        for bi, box in enumerate(boxes):
            for fi, (idx, n) in enumerate(FACES):
                u0, v0, u1, v1 = box.face_regions.get(fi, box.region)
                base = len(self.uv)
                self.uv += [(u0 / 64.0, v0 / 64.0), (u1 / 64.0, v0 / 64.0), (u1 / 64.0, v1 / 64.0), (u0 / 64.0, v1 / 64.0)]
                self.tris += [(base, base + 1, base + 2), (base, base + 2, base + 3)]

    def frame(self, xforms):
        """xforms[i] = funcion que transforma las esquinas de la caja i."""
        out = []
        for bi, box in enumerate(self.boxes):
            pts = box.verts(xforms[bi])
            for idx, n in FACES:
                quad = [pts[i] for i in idx]
                a = [quad[1][k] - quad[0][k] for k in range(3)]
                b = [quad[2][k] - quad[0][k] for k in range(3)]
                nrm = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
                ln = math.sqrt(sum(c * c for c in nrm)) or 1
                nrm = tuple(c / ln for c in nrm)
                for q in quad:
                    out.append((q, nrm))
        return out


def enc_normal(n):
    lng = math.acos(max(-1, min(1, n[2])))
    lat = math.atan2(n[1], n[0])
    return (int(round(lat * 255 / (2 * math.pi))) & 255) << 8 | (int(round(lng * 255 / (2 * math.pi))) & 255)


def write_md3(path, name, mesh, frames, texture_name):
    """frames: lista de listas de (pos, normal) en el orden de Mesh.frame()."""
    nv, nt, nf = len(mesh.uv), len(mesh.tris), len(frames)
    surf_hdr, fr_sz = 108, 56
    ofs_tri = surf_hdr
    ofs_sh = ofs_tri + nt * 12
    ofs_st = ofs_sh + 68
    ofs_xyz = ofs_st + nv * 8
    ofs_end = ofs_xyz + nf * nv * 8
    ofs_frames = 108
    ofs_surf = ofs_frames + nf * fr_sz
    total = ofs_surf + ofs_end
    b = bytearray()
    b += b"IDP3" + struct.pack("<i", 15) + name.encode().ljust(64, b"\0")
    b += struct.pack("<iiiiiiii", 0, nf, 0, 1, 0, ofs_frames, ofs_surf, ofs_surf, ) [:0]
    b += struct.pack("<i", 0)              # flags
    b += struct.pack("<iiii", nf, 0, 1, 0)  # frames, tags, surfaces, skins
    b += struct.pack("<iiii", ofs_frames, ofs_surf, ofs_surf, total)  # ofs_frames, ofs_tags, ofs_surfaces, ofs_eof
    for fi, fr in enumerate(frames):
        xs = [p[0][0] for p in fr]; ys = [p[0][1] for p in fr]; zs = [p[0][2] for p in fr]
        mn, mx = (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))
        rad = max(math.sqrt(sum(c * c for c in v)) for v in (mn, mx))
        b += struct.pack("<3f3f3ff", *mn, *mx, 0, 0, 0, rad) + ("f%d" % fi).encode().ljust(16, b"\0")
    s = bytearray()
    s += b"IDP3" + b"body".ljust(64, b"\0")
    s += struct.pack("<iiiiiiiiii", 0, nf, 1, nv, nt, ofs_tri, ofs_sh, ofs_st, ofs_xyz, ofs_end)
    for t in mesh.tris:
        s += struct.pack("<iii", *t)
    s += texture_name.encode().ljust(64, b"\0") + struct.pack("<i", 0)
    for u, v in mesh.uv:
        s += struct.pack("<ff", u, v)
    for fr in frames:
        for pos, nrm in fr:
            s += struct.pack("<hhhH", *(int(round(c * 64)) for c in pos), enc_normal(nrm))
    assert len(s) == ofs_end, (len(s), ofs_end)
    b += s
    assert len(b) == total, (len(b), total)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(b)


# ---------------------------------------------------------------- zombie
def zombie():
    boxes = [
        Box(-4, 4, 1, 8, -24, 0, PANTS),            # 0 pierna izquierda
        Box(-4, 4, -8, -1, -24, 0, PANTS),          # 1 pierna derecha
        Box(-5, 5, -9, 9, 0, 20, SHIRT),            # 2 torso
        Box(-5, 5, -5, 5, 21, 32, SKIN, {0: FACE}),  # 3 cabeza (cara hacia +x)
        Box(0, 20, 9, 14, 13, 19, SHIRT),           # 4 brazo izquierdo
        Box(0, 20, -14, -9, 13, 19, SHIRT),         # 5 brazo derecho
        Box(20, 25, 9, 14, 13, 19, SKIN),           # 6 mano izquierda
        Box(20, 25, -14, -9, 13, 19, SKIN),         # 7 mano derecha
        Box(-2, 2, -2.5, 2.5, 19.5, 23, SKIN),      # 8 cuello
        Box(0.5, 5.2, -3.6, 3.6, 17.5, 21.5, BONE, {0: FACE}),   # 9 mandibula colgando
        Box(-6, 6.5, -9.8, 9.8, -7, 2, RAGS),       # 10 camisa rota (faldon)
        Box(5, 5.8, -4.5, 4, 5, 16, RIBS),          # 11 costillas expuestas
        Box(-6, -4, -10.5, 10.5, 15, 21, RAGS),     # 12 hombros/espalda andrajosos
        Box(6, 11, 9.5, 13.5, 13.5, 18.5, RAGS),    # 13 manga rota izq
    ]
    mesh = Mesh(boxes)
    hip, sh_l, sh_r = (0, 0, 0), (0, 11.5, 18), (0, -11.5, 18)

    def pose(leg, arm, lean, bob=0.0, whole=0.0, whole_pivot=(0, 0, -24), drop=0.0):
        def comp(*fs):
            def f(p):
                for g in fs:
                    p = g(p)
                return p
            return f
        sh_up = lambda pv, a: (lambda p: rot_y(p, pv, a))
        body = lambda p: rot_y(p, hip, lean)
        glob = lambda p: (lambda q: (q[0], q[1], q[2] + bob - drop))(rot_y(p, whole_pivot, whole))
        legL = comp(sh_up(hip, leg), glob)
        legR = comp(sh_up(hip, -leg), glob)
        torso = comp(body, glob)
        armL = comp(sh_up(sh_l, arm), body, glob)
        armR = comp(sh_up(sh_r, arm), body, glob)
        headT = comp(sh_up((0, 0, 21), 20), body, glob)          # cabeza caida hacia delante
        jawT = comp(sh_up((0, 0, 21), 20 + 14 + 8 * math.sin(bob * 3)), body, glob)
        sleeve = comp(sh_up(sh_l, arm * 0.5), body, glob)
        return [legL, legR, torso, headT, armL, armR, armL, armR, torso, jawT, torso, torso, torso, sleeve]

    frames = []
    for i in range(8):                               # caminar
        ph = 2 * math.pi * i / 8
        frames.append(mesh.frame(pose(32 * math.sin(ph), -6 + 7 * math.sin(2 * ph), 9, bob=1.2 * abs(math.sin(ph)))))
    for arm, lean in ((-35, 10), (-85, 6), (-10, 18), (35, 24)):   # atacar (manos arriba y golpe)
        frames.append(mesh.frame(pose(8, arm, lean)))
    for fall, drop in ((-12, 0), (-40, 3), (-70, 8), (-90, 14)):   # morir cayendo hacia atras
        frames.append(mesh.frame(pose(0, 40 + (-fall) * 0.3, 4, whole=fall, drop=0)))
    return mesh, frames


# ---------------------------------------------------------------- armas
def gun(kind):
    arm = Box(-14, 4, -9, -5, -13, -8, CLOTH)          # manga / antebrazo derecho
    hand = Box(3, 11, -9, -5, -13, -7, SKIN)
    thumb = Box(8, 12, -5, -3.6, -9.5, -7.5, SKIN)     # pulgar sobre la empunadura
    lhand = Box(14, 20, -3.5, 1, -12, -8, SKIN)        # mano de apoyo (delante)
    lsleeve = Box(6, 14, -3.5, 1.2, -13, -9, CLOTH)
    if kind == "pistol":
        parts = [Box(8, 20, -7, -4, -6, -3, METAL),            # corredera
                 Box(8.5, 19.5, -6.6, -4.4, -3, -2.4, LIGHT),   # tapa / ranuras superiores
                 Box(8, 13, -7, -4, -12, -6, METAL),            # empunadura
                 Box(8.5, 12.5, -7.4, -3.6, -11.5, -7, WOOD),   # cachas
                 Box(13, 19, -6.4, -4.6, -8.2, -6, METAL),      # armazon
                 Box(13.5, 17, -6.2, -4.8, -9.6, -8.2, METAL),  # guardamonte
                 Box(20, 22.5, -6.2, -4.8, -5.5, -3.5, LIGHT),  # canon
                 Box(8, 9.5, -5.4, -5.0, -3.2, -2.4, LIGHT),    # mira trasera
                 Box(19, 20, -5.4, -5.0, -3.0, -2.2, LIGHT),    # mira delantera
                 Box(11.5, 13.2, -5.6, -5.0, -7, -6.3, LIGHT)]  # gatillo
    elif kind == "smg":
        parts = [Box(6, 24, -7, -4, -7, -2, METAL),             # cuerpo
                 Box(7, 23, -6.6, -4.4, -2, -1.2, LIGHT),        # riel superior
                 Box(24, 33, -6, -5, -5.5, -3.5, LIGHT),         # canon
                 Box(33, 36, -6.4, -4.6, -6, -3, METAL),         # supresor / freno
                 Box(12, 15, -6.5, -4.5, -17, -7, METAL),        # cargador largo
                 Box(11.5, 15.5, -6.8, -4.2, -17.6, -16.5, LIGHT),
                 Box(7, 10, -7, -4, -12, -7, METAL),             # empunadura
                 Box(-3, 6, -6.5, -4.5, -6, -2.5, WOOD),         # culata
                 Box(-6, -3, -6.8, -4.2, -7, -2, METAL),         # contera
                 Box(16, 22, -7.5, -3.5, -8, -7, WOOD),          # cubremanos
                 Box(8, 11, -5.8, -5.2, -1.2, 0.6, LIGHT),       # mira
                 Box(22, 23.2, -5.6, -5.0, -1.2, 0.2, LIGHT)]
    elif kind == "shotgun":
        parts = [Box(8, 38, -6.5, -4.5, -5, -3, METAL),         # canon superior
                 Box(8, 30, -6.5, -4.5, -7.5, -5, METAL),        # tubo del cargador
                 Box(38, 39.5, -6.2, -4.8, -4.8, -3.2, LIGHT),   # boca
                 Box(30, 32, -6.9, -4.1, -8, -5, LIGHT),         # tapon
                 Box(16, 27, -7.5, -3.5, -9, -5, WOOD),          # guardamano corredizo
                 Box(17, 26, -7.8, -3.2, -9.4, -8.6, METAL),
                 Box(-8, 10, -7, -4, -9, -3, WOOD),              # culata
                 Box(-10, -8, -7.2, -3.8, -9.6, -2.6, METAL),    # cantonera
                 Box(8, 14, -7, -4, -9, -4, METAL),              # recamara
                 Box(8.5, 13, -7.6, -3.4, -6.5, -5.2, LIGHT),    # ventana de expulsion
                 Box(37, 38, -5.8, -5.2, -3.2, -2.2, LIGHT)]     # mira
    else:
        parts = [Box(-8, 12, -7, -4, -9, -3, WOOD),             # culata
                 Box(-10, -8, -7.2, -3.8, -9.8, -2.4, METAL),
                 Box(-2, 8, -6.2, -4.8, -3, -1.6, WOOD),          # carrillera
                 Box(10, 24, -7, -4, -6, -2.5, METAL),           # caja del mecanismo
                 Box(11, 22, -6.5, -4.5, -2.5, -1.5, LIGHT),     # cubierta
                 Box(24, 44, -6, -5, -5, -3.5, LIGHT),           # canon
                 Box(44, 46, -6.4, -4.6, -5.4, -3.1, METAL),     # freno de boca
                 Box(14, 24, -7.5, -3.5, -9, -5.5, WOOD),        # guardamano
                 Box(24, 34, -6.6, -4.4, -6.5, -5, WOOD),        # cubierta del canon
                 Box(12, 20, -6.5, -4.5, -2.5, 0.5, LIGHT),      # mira telescopica
                 Box(10.5, 12, -6.9, -4.1, -2.9, 0.9, METAL),
                 Box(20, 21.5, -6.9, -4.1, -2.9, 0.9, METAL),
                 Box(15, 18, -9.5, -7.5, -5, -3.6, METAL),       # cerrojo (palanca)
                 Box(14, 17, -6.8, -4.2, -11, -9, METAL)]        # cargador
    boxes = [arm, hand, thumb, lhand, lsleeve] + parts
    mesh = Mesh(boxes)

    def pose(dx=0.0, dz=0.0, pitch=0.0):
        pv = (6, -5, -6)
        f = lambda p: (lambda q: (q[0] + dx, q[1], q[2] + dz))(rot_y(p, pv, pitch))
        return [f] * len(boxes)
    frames = [mesh.frame(pose())]
    for dx, dz, pt in ((-3.5, 0.6, -6), (-2.0, 0.3, -3), (-0.6, 0.1, -1)):    # retroceso
        frames.append(mesh.frame(pose(dx, dz, pt)))
    for dx, dz, pt in ((0, -2, 8), (0, -7, 22), (0, -7, 22), (0, -1, 6)):      # recarga: baja y se inclina
        frames.append(mesh.frame(pose(dx, dz, pt)))
    return mesh, frames


# ---------------------------------------------------------------- texturas de los modelos
def save_tga(path, w, h, px):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 24, 0x20))
        f.write(b"".join(bytes((p[2], p[1], p[0])) for p in px))


def region_fill(px, r, color, rng, grain=10):
    u0, v0, u1, v1 = r
    for y in range(v0 - 1, v1 + 2):
        for x in range(u0 - 1, u1 + 2):
            n = rng.uniform(-grain, grain)
            px[y * 64 + x] = tuple(max(0, min(255, int(c + n))) for c in color)


def splat(px, r, rng, n, color, size=(1, 4)):
    u0, v0, u1, v1 = r
    for _ in range(n):
        cx, cy = rng.randint(u0, u1), rng.randint(v0, v1)
        rad = rng.randint(*size)
        for y in range(cy - rad, cy + rad + 1):
            for x in range(cx - rad, cx + rad + 1):
                if u0 <= x <= u1 and v0 <= y <= v1 and (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                    k = rng.uniform(0.8, 1.1)
                    px[y * 64 + x] = tuple(max(0, min(255, int(c * k))) for c in color)


def make_textures(outdir):
    rng = random.Random(5)
    z = [(0, 0, 0)] * 4096
    region_fill(z, SKIN, (138, 154, 120), rng, 9)           # piel gris verdosa
    splat(z, SKIN, rng, 14, (70, 86, 74), (1, 3))          # venas / moretones
    splat(z, SKIN, rng, 9, (95, 20, 16), (1, 3))           # sangre
    region_fill(z, SHIRT, (128, 112, 90), rng, 14)           # camisa sucia
    splat(z, SHIRT, rng, 16, (118, 24, 20), (1, 4))        # manchas de sangre
    splat(z, SHIRT, rng, 8, (30, 24, 20), (1, 3))          # agujeros / mugre
    region_fill(z, PANTS, (74, 84, 108), rng, 10)
    splat(z, PANTS, rng, 10, (28, 30, 38), (1, 3))
    splat(z, PANTS, rng, 6, (100, 22, 18), (1, 3))
    region_fill(z, FACE, (134, 150, 118), rng, 8)
    region_fill(z, RAGS, (96, 82, 66), rng, 16)
    splat(z, RAGS, rng, 14, (22, 18, 16), (1, 3))
    splat(z, RAGS, rng, 8, (110, 24, 20), (1, 3))
    region_fill(z, RIBS, (150, 90, 84), rng, 10)
    for yy in range(RIBS[1], RIBS[3], 3):                  # costillas
        for xx in range(RIBS[0], RIBS[2]):
            z[yy * 64 + xx] = (205, 195, 170)
            z[(yy + 1) * 64 + xx] = (60, 18, 16)
    region_fill(z, BONE, (170, 164, 140), rng, 8)
    splat(z, BONE, rng, 6, (110, 26, 20), (1, 3))
    # cara: ojos hundidos con brillo, nariz, boca con dientes y barbilla ensangrentada
    for ex in (38, 51):
        for y in range(8, 14):
            for x in range(ex, ex + 6):
                z[y * 64 + x] = (22, 14, 12)
        for y in range(10, 13):
            for x in range(ex + 1, ex + 5):
                z[y * 64 + x] = (255, 200, 40)
    for y in range(15, 19):
        for x in range(46, 49):
            z[y * 64 + x] = (60, 70, 55)
    for y in range(21, 26):
        for x in range(38, 58):
            z[y * 64 + x] = (40, 12, 12)
    for x in range(38, 58, 3):
        for y in (21, 22):
            z[y * 64 + x] = (225, 220, 195)
    splat(z, (36, 22, 60, 29), rng, 10, (120, 18, 14), (1, 3))
    save_tga(os.path.join(outdir, "models", "zombie.tga"), 64, 64, z)
    g = [(0, 0, 0)] * 4096
    region_fill(g, METAL, (46, 48, 54), rng, 6)
    region_fill(g, WOOD, (112, 76, 42), rng, 10)
    region_fill(g, LIGHT, (120, 124, 132), rng, 6)
    region_fill(g, CLOTH, (60, 78, 52), rng, 8)
    region_fill(g, SKIN, (200, 160, 130), rng, 6)
    save_tga(os.path.join(outdir, "models", "gun.tga"), 64, 64, g)


# ---------------------------------------------------------------- vista previa (solo para revisar)
def preview(path_png, mesh, frames, sel, view="side", scale=3.0, cols=8):
    from PIL import Image, ImageDraw
    cell = 190
    img = Image.new("RGB", (cell * min(cols, len(sel)), cell * ((len(sel) + cols - 1) // cols)), (30, 30, 36))
    d = ImageDraw.Draw(img)
    for n, fi in enumerate(sel):
        ox, oy = (n % cols) * cell + cell / 2, (n // cols) * cell + cell * 0.62
        polys = []
        fr = frames[fi]
        for q in range(0, len(fr), 4):
            quad = fr[q:q + 4]
            if view == "side":
                pts = [(ox + p[0][0] * scale, oy - p[0][2] * scale) for p in quad]
                depth = sum(p[0][1] for p in quad) / 4
            else:
                pts = [(ox + p[0][1] * scale, oy - p[0][2] * scale) for p in quad]
                depth = sum(p[0][0] for p in quad) / 4
            nrm = quad[0][1]
            light = 0.45 + 0.55 * max(0, nrm[2] * 0.5 + nrm[0] * 0.3 + nrm[1] * -0.4 + 0.3)
            polys.append((depth, pts, light, nrm))
        polys.sort(key=lambda t: t[0], reverse=(view == "side"))
        for depth, pts, light, nrm in polys:
            facing = nrm[1] < 0.05 if view == "side" else nrm[0] > -0.05
            col = int(60 + 150 * light)
            d.polygon(pts, fill=(col, int(col * 0.9), int(col * 0.8)), outline=(20, 20, 20))
    img.save(path_png)


def main(out, prev=None):
    make_textures(out)
    mesh, frames = zombie()
    write_md3(os.path.join(out, "models", "zombie.md3"), "zombie", mesh, frames, "models/zombie.tga")
    if prev:
        preview(os.path.join(prev, "prev_zombie.png"), mesh, frames, list(range(16)))
    for k in ("pistol", "smg", "shotgun", "rifle"):
        gm, gf = gun(k)
        write_md3(os.path.join(out, "models", "v_%s.md3" % k), k, gm, gf, "models/gun.tga")
        if prev:
            preview(os.path.join(prev, "prev_%s.png" % k), gm, gf, [0, 1, 6], scale=5.5)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build/pak", sys.argv[2] if len(sys.argv) > 2 else None)
