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
    def __init__(self, boxes, size=64):
        self.boxes = boxes
        self.uv, self.tris = [], []
        S = float(size)
        for bi, box in enumerate(boxes):
            for fi, (idx, n) in enumerate(FACES):
                u0, v0, u1, v1 = box.face_regions.get(fi, box.region)
                if fi < 4:      # caras laterales: las dos primeras esquinas son las de abajo
                    v0, v1 = v1, v0
                base = len(self.uv)
                self.uv += [(u0 / S, v0 / S), (u1 / S, v0 / S), (u1 / S, v1 / S), (u0 / S, v1 / S)]
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
# Atlas de 128x128 en 16 celdas de 32x32 (30x30 utiles)
ZS = 128


def zcell(i, j):
    return (32 * i + 1, 32 * j + 1, 32 * i + 31, 32 * j + 31)


Z_JFRONT, Z_JBACK, Z_JACKET, Z_FACE = zcell(0, 0), zcell(1, 0), zcell(2, 0), zcell(3, 0)
Z_PANTS, Z_SKIN, Z_ARM, Z_GLOVE = zcell(0, 1), zcell(1, 1), zcell(2, 1), zcell(3, 1)
Z_CAPTOP, Z_CAPBAND, Z_BELT, Z_RED = zcell(0, 2), zcell(1, 2), zcell(2, 2), zcell(3, 2)
Z_COLLAR, Z_JAW, Z_METAL, Z_LEG = zcell(0, 3), zcell(1, 3), zcell(2, 3), zcell(3, 3)


def zombie():
    """Zombie con gorra de oficial, chaqueta blanca manchada, tirantes, brazalete rojo liso,
    pantalon verde roto, guantes oscuros y pies descalzos."""
    boxes, keys = [], []

    def add(key, *a, **kw):
        boxes.append(Box(*a, **kw))
        keys.append(key)

    for key, s in (("legL", 1), ("legR", -1)):
        y = lambda a, b: (min(a * s, b * s), max(a * s, b * s))
        add(key, -4.2, 4.2, *y(0.8, 8.4), -16, 0, Z_PANTS)           # pantalon
        add(key, -2.6, 2.6, *y(2.6, 6.6), -21.5, -16, Z_LEG)         # espinilla al aire
        add(key, -2.5, 7, *y(2.4, 6.8), -24, -21.5, Z_LEG)           # pie descalzo
    add("torso", -5, 5, -9, 9, 0, 20, Z_JACKET, {0: Z_JFRONT, 1: Z_JBACK})   # chaqueta
    add("torso", -5.8, 5.8, -9.6, 9.6, -4, 1.5, Z_JACKET)                     # faldon
    add("torso", -5.4, 5.4, -9.4, 9.4, 1.5, 4, Z_BELT)                        # cinturon
    add("torso", 5.3, 5.9, -1.8, 1.8, 1.7, 3.8, Z_METAL)                      # hebilla
    add("torso", -4, 4, -10.4, 10.4, 17, 19.6, Z_JACKET)                      # hombros
    add("torso", -4.6, 4.8, -5.6, 5.6, 19, 21.5, Z_COLLAR)                    # cuello de la chaqueta
    add("torso", -2, 2, -2.5, 2.5, 19.5, 23, Z_SKIN)                          # cuello
    add("headT", -5, 5, -5, 5, 21, 32, Z_SKIN, {0: Z_FACE})                   # cabeza (cara hacia +x)
    add("jawT", 0.5, 5.2, -3.6, 3.6, 17.5, 21.5, Z_JAW)                       # mandibula colgando
    add("headT", -5.4, 5.4, -5.4, 5.4, 29.2, 31.2, Z_CAPBAND)                 # gorra: banda
    add("headT", -5.4, 4.4, -5.4, 5.4, 31.2, 33.2, Z_CAPTOP)                  # gorra: copa
    add("headT", -6.2, 5.0, -6.2, 6.2, 33.2, 34.8, Z_CAPTOP)                  # gorra: plato alto
    add("headT", 5.2, 9.2, -4.2, 4.2, 29.6, 30.6, Z_CAPBAND)                  # gorra: visera
    for key, s in (("armL", 1), ("armR", -1)):
        y = lambda a, b: (min(a * s, b * s), max(a * s, b * s))
        add(key, 0, 13, *y(9, 14), 13, 19, Z_JACKET)                          # manga
        add(key, 13, 20, *y(9.4, 13.6), 13.6, 18.4, Z_ARM)                    # antebrazo al aire
        add(key, 20, 25.5, *y(9.2, 13.8), 13.2, 18.8, Z_GLOVE)                # guante
        add(key, 25.5, 29, *y(9.8, 13.2), 14.4, 17.6, Z_GLOVE)                # dedos
    add("armL", 4.5, 8, 8.7, 14.3, 12.7, 19.3, Z_RED)                         # brazalete rojo (liso)

    mesh = Mesh(boxes, ZS)
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
        T = {
            "legL": comp(sh_up(hip, leg), glob),
            "legR": comp(sh_up(hip, -leg), glob),
            "torso": comp(body, glob),
            "armL": comp(sh_up(sh_l, arm), body, glob),
            "armR": comp(sh_up(sh_r, arm), body, glob),
            "headT": comp(sh_up((0, 0, 21), 20), body, glob),           # cabeza caida hacia delante
            "jawT": comp(sh_up((0, 0, 21), 20 + 14 + 8 * math.sin(bob * 3)), body, glob),
        }
        return [T[k] for k in keys]

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


def region_fill(px, r, color, rng, grain=10, W=64):
    u0, v0, u1, v1 = r
    for y in range(max(0, v0 - 1), min(W - 1, v1 + 1) + 1):
        for x in range(max(0, u0 - 1), min(W - 1, u1 + 1) + 1):
            n = rng.uniform(-grain, grain)
            px[y * W + x] = tuple(max(0, min(255, int(c + n))) for c in color)


def splat(px, r, rng, n, color, size=(1, 4), W=64):
    u0, v0, u1, v1 = r
    for _ in range(n):
        cx, cy = rng.randint(u0, u1), rng.randint(v0, v1)
        rad = rng.randint(*size)
        for y in range(cy - rad, cy + rad + 1):
            for x in range(cx - rad, cx + rad + 1):
                if u0 <= x <= u1 and v0 <= y <= v1 and (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                    k = rng.uniform(0.8, 1.1)
                    px[y * W + x] = tuple(max(0, min(255, int(c * k))) for c in color)


def make_zombie_texture(outdir):
    rng = random.Random(7)
    W = ZS
    z = [(0, 0, 0)] * (W * W)

    def fill(r, c, g=8):
        region_fill(z, r, c, rng, g, W)

    def sp(r, n, c, size=(1, 3)):
        splat(z, r, rng, n, c, size, W)

    def put(r, x, y, c):                # coordenadas locales de la celda (0..29)
        X, Y = r[0] + x, r[1] + y
        if r[0] <= X <= r[2] and r[1] <= Y <= r[3]:
            z[Y * W + X] = c

    def rect(r, x0, y0, x1, y1, c, g=0):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                k = rng.uniform(-g, g) if g else 0
                put(r, x, y, tuple(max(0, min(255, int(v + k))) for v in c))

    WHITE, BLOOD, DRY, DIRT = (208, 203, 190), (128, 36, 26), (84, 30, 24), (176, 160, 118)

    def jacket(r):
        fill(r, WHITE, 9)
        for x in range(0, 30, 3):                               # vetas de mugre
            if rng.random() < 0.6:
                rect(r, x, rng.randint(0, 8), x, rng.randint(14, 29), (190, 184, 168), 4)
        sp(r, 12, DIRT, (1, 3))
        sp(r, 6, BLOOD, (1, 2))
        sp(r, 4, DRY, (1, 2))

    # --- chaqueta: frente con solapas verdes, tirantes, botones y bolsillos
    jacket(Z_JFRONT)
    r = Z_JFRONT
    for y in range(0, 10):
        hw = max(1, 6 - y // 2)
        rect(r, 15 - hw, y, 15 + hw, y, (122, 124, 110), 3)                       # piel del cuello
        rect(r, 15 - hw - 5, y, 15 - hw - 1, y, (66, 84, 60), 4)                  # solapa
        rect(r, 15 + hw + 1, y, 15 + hw + 5, y, (66, 84, 60), 4)
    for sx in (9, 21):                                                            # tirantes
        rect(r, sx - 1, 6, sx + 1, 29, (74, 50, 34), 5)
        rect(r, sx - 1, 6, sx - 1, 29, (50, 34, 24))
    for yy in (13, 19, 25):                                                       # botones
        rect(r, 14, yy, 15, yy + 1, (150, 146, 130))
    for x0, x1 in ((3, 8), (22, 27)):                                             # bolsillos
        rect(r, x0, 14, x1, 14, (150, 144, 130))
        rect(r, x0, 14, x0, 21, (150, 144, 130))
        rect(r, x1, 14, x1, 21, (150, 144, 130))
    rect(r, 23, 9, 27, 13, BLOOD, 18)                                             # gran mancha
    rect(r, 3, 21, 5, 24, (140, 40, 30), 14)
    sp(r, 3, BLOOD, (2, 3))
    # --- espalda con tirantes en Y
    jacket(Z_JBACK)
    r = Z_JBACK
    for t in range(0, 22):
        rect(r, 9 + int(t * 0.27), t, 10 + int(t * 0.27), t, (74, 50, 34), 4)
        rect(r, 20 - int(t * 0.27), t, 21 - int(t * 0.27), t, (74, 50, 34), 4)
    rect(r, 14, 22, 16, 29, (74, 50, 34), 4)
    sp(r, 3, BLOOD, (2, 3))
    jacket(Z_JACKET)
    # --- piel
    fill(Z_SKIN, (150, 150, 136), 8)
    sp(Z_SKIN, 14, (96, 108, 100), (1, 3))
    sp(Z_SKIN, 8, (112, 30, 24), (1, 3))
    fill(Z_ARM, (142, 142, 124), 8)
    sp(Z_ARM, 12, (120, 32, 26), (1, 4))
    sp(Z_ARM, 8, (92, 100, 88), (1, 3))
    fill(Z_LEG, (160, 140, 114), 8)
    sp(Z_LEG, 14, (92, 78, 60), (1, 4))
    sp(Z_LEG, 6, (112, 34, 26), (1, 3))
    # --- guantes
    fill(Z_GLOVE, (52, 44, 40), 7)
    sp(Z_GLOVE, 14, (84, 74, 66), (1, 3))
    sp(Z_GLOVE, 5, (100, 28, 22), (1, 2))
    # --- pantalon verde roto
    fill(Z_PANTS, (92, 104, 72), 8)
    sp(Z_PANTS, 16, (60, 68, 48), (1, 4))
    sp(Z_PANTS, 12, (120, 128, 94), (1, 3))
    sp(Z_PANTS, 3, (110, 34, 26), (1, 2))
    for x in range(0, 30):                                                       # borde roto abajo
        h = (x * 7) % 5
        if h < 3:
            rect(Z_PANTS, x, 26 + h, x, 29, (150, 134, 112), 5)
    for cx, cy in ((7, 14), (21, 10), (14, 21)):                                  # desgarros con herida
        rect(Z_PANTS, cx, cy, cx + 3, cy + 5, (150, 136, 114), 5)
        rect(Z_PANTS, cx + 1, cy + 2, cx + 2, cy + 3, (120, 34, 26), 8)
    # --- gorra, cinturon, brazalete, cuello, metal
    fill(Z_CAPTOP, (80, 86, 72), 6)
    sp(Z_CAPTOP, 8, (54, 58, 48), (1, 3))
    sp(Z_CAPTOP, 3, (110, 32, 26), (1, 2))
    fill(Z_CAPBAND, (34, 32, 30), 5)
    for y in range(3, 30, 6):
        rect(Z_CAPBAND, 0, y, 29, y, (58, 54, 50), 3)
    fill(Z_BELT, (66, 46, 32), 6)
    sp(Z_BELT, 6, (36, 26, 18), (1, 2))
    fill(Z_RED, (156, 32, 30), 10)
    for y in range(4, 30, 7):
        rect(Z_RED, 0, y, 29, y, (120, 22, 22), 4)
    sp(Z_RED, 8, (76, 16, 14), (1, 4))
    fill(Z_COLLAR, (62, 80, 58), 7)
    sp(Z_COLLAR, 6, (112, 32, 26), (1, 2))
    fill(Z_METAL, (176, 164, 118), 8)
    # --- mandibula: dientes arriba, encia y sangre
    fill(Z_JAW, (150, 42, 38), 8)
    rect(Z_JAW, 0, 0, 29, 8, (216, 208, 182), 6)
    for x in range(2, 30, 3):
        rect(Z_JAW, x, 0, x, 8, (96, 70, 56))
    rect(Z_JAW, 0, 9, 29, 10, (90, 20, 18))
    sp(Z_JAW, 8, (120, 18, 14), (1, 3))
    # --- cara
    f = Z_FACE
    fill(f, (150, 151, 138), 7)
    sp(f, 16, (100, 112, 104), (1, 3))                                           # venas
    for y in range(30):                                                          # sombra en los bordes
        for x in (0, 1, 2, 27, 28, 29):
            put(f, x, y, (118, 120, 108))
    for cx in (7, 23):                                                           # mejillas hundidas
        for y in range(15, 24):
            for x in range(cx - 3, cx + 4):
                if (x - cx) ** 2 + ((y - 19) * 0.8) ** 2 <= 11:
                    put(f, x, y, (116, 118, 108))
    for ex in (5, 19):                                                           # cuencas y ojos
        rect(f, ex, 10, ex + 6, 15, (44, 36, 32), 4)
        rect(f, ex + 1, 11, ex + 5, 14, (30, 22, 20))
        rect(f, ex + 2, 12, ex + 4, 13, (255, 222, 60))
        put(f, ex + 2, 12, (255, 250, 190))
        put(f, ex + 1, 12, (235, 150, 30)); put(f, ex + 5, 13, (235, 150, 30))
    for x0, x1 in ((4, 10), (19, 25)):                                           # ceja / frente
        rect(f, x0, 8, x1, 8, (98, 98, 88))
    rect(f, 14, 16, 15, 19, (70, 60, 52))                                         # nariz
    rect(f, 13, 20, 13, 20, (46, 28, 26)); rect(f, 16, 20, 16, 20, (46, 28, 26))
    rect(f, 8, 22, 22, 27, (62, 12, 10), 3)                                      # boca abierta
    for x in range(8, 23, 2):
        rect(f, x, 22, x, 23, (226, 218, 190))
        if x % 4 == 0:
            rect(f, x, 26, x, 27, (218, 208, 178))
    for x in (9, 14, 20):                                                        # sangre por la barbilla
        rect(f, x, 24, x, rng.randint(28, 29), (136, 22, 18), 8)
    sp(f, 6, (130, 20, 16), (1, 3))
    save_tga(os.path.join(outdir, "models", "zombie.tga"), ZS, ZS, z)


def make_textures(outdir):
    rng = random.Random(5)
    make_zombie_texture(outdir)
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
