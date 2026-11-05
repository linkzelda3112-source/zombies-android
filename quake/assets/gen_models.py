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


class Loft:
    """Superficie redondeada: anillos elipticos a lo largo de un eje ('z' o 'x').
    rings: (pos, c1, c2, r1, r2). eje z: centro (x,y), radios (x,y); eje x: centro (y,z), radios (y,z).
    El primer anillo es la parte de arriba de la textura (v=0)."""
    def __init__(self, axis, rings, region, seg=12):
        self.axis, self.rings, self.region, self.N = axis, rings, region, seg
        self.R = len(rings)

    def point(self, i, j):
        pos, c1, c2, r1, r2 = self.rings[i]
        th = -math.pi + 2 * math.pi * j / self.N
        a, b = c1 + r1 * math.cos(th), c2 + r2 * math.sin(th)
        return (a, b, pos) if self.axis == "z" else (pos, a, b)

    def grid(self, xform):
        return [xform(self.point(i, j)) for i in range(self.R) for j in range(self.N + 1)]

    def pos_at(self, fv):
        k = max(0.0, min(1.0, fv)) * (self.R - 1)
        i = min(int(k), self.R - 2)
        f = k - i
        return self.rings[i][0] * (1 - f) + self.rings[i + 1][0] * f


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


class Mesh:
    """Lista fija de triangulos/UV; cada cuadro solo cambia las posiciones."""
    def __init__(self, boxes, size=64):
        self.boxes = boxes
        self.uv, self.tris, self.info = [], [], []
        S = float(size)
        for bi, box in enumerate(boxes):
            if isinstance(box, Loft):
                base, N, R = len(self.uv), box.N, box.R
                u0, v0, u1, v1 = box.region
                for i in range(R):
                    for j in range(N + 1):
                        self.uv.append(((u0 + (u1 - u0) * j / N) / S, (v0 + (v1 - v0) * i / (R - 1)) / S))
                tris = []
                for i in range(R - 1):
                    for j in range(N):
                        a = base + i * (N + 1) + j
                        c = a + N + 1
                        tris += [(a, a + 1, c + 1), (a, c + 1, c)]
                rest = box.grid(lambda p: p)
                cen = [sum(p[k] for p in rest) / len(rest) for k in range(3)]
                sgn = 0.0
                for a, b, c in tris:
                    pa, pb, pc = rest[a - base], rest[b - base], rest[c - base]
                    n = _cross(_sub(pb, pa), _sub(pc, pa))
                    m = [(pa[k] + pb[k] + pc[k]) / 3 - cen[k] for k in range(3)]
                    sgn += sum(n[k] * m[k] for k in range(3))
                if sgn < 0:
                    tris = [(a, c, b) for a, b, c in tris]
                t0 = len(self.tris)
                self.tris += tris
                self.info.append((base, t0, len(self.tris)))
                continue
            self.info.append(None)
            for fi, (idx, n) in enumerate(FACES):
                u0, v0, u1, v1 = box.face_regions.get(fi, box.region)
                if fi < 4:      # caras laterales: las dos primeras esquinas son las de abajo
                    v0, v1 = v1, v0
                base = len(self.uv)
                self.uv += [(u0 / S, v0 / S), (u1 / S, v0 / S), (u1 / S, v1 / S), (u0 / S, v1 / S)]
                self.tris += [(base, base + 1, base + 2), (base, base + 2, base + 3)]

    def frame(self, xforms):
        """xforms[i] = funcion que transforma los puntos de la parte i."""
        out = []
        for bi, box in enumerate(self.boxes):
            if isinstance(box, Loft):
                base, t0, t1 = self.info[bi]
                g = box.grid(xforms[bi])
                acc = [[0.0, 0.0, 0.0] for _ in g]
                for a, b, c in self.tris[t0:t1]:
                    n = _cross(_sub(g[b - base], g[a - base]), _sub(g[c - base], g[a - base]))
                    for k in (a, b, c):
                        for m in range(3):
                            acc[k - base][m] += n[m]
                for i in range(box.R):                    # unir la costura
                    p, q = i * (box.N + 1), i * (box.N + 1) + box.N
                    s = [acc[p][m] + acc[q][m] for m in range(3)]
                    acc[p], acc[q] = list(s), list(s)
                for p, n in zip(g, acc):
                    ln = math.sqrt(sum(c * c for c in n))
                    out.append((p, tuple(c / ln for c in n) if ln > 1e-9 else (0.0, 0.0, 1.0)))
                continue
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
# Atlas de 256x256 en 16 celdas de 64x64 (62x62 utiles); las zonas "envolventes" ocupan 2 celdas de ancho.
ZS = 256


def zcell(i, j, w=1):
    return (64 * i + 1, 64 * j + 1, 64 * (i + w) - 1, 64 * j + 63)


Z_HEAD, Z_TORSO = zcell(0, 0, 2), zcell(2, 0, 2)
Z_PANTS, Z_LEG, Z_SLEEVE, Z_ARM = zcell(0, 1), zcell(1, 1), zcell(2, 1), zcell(3, 1)
Z_GLOVE, Z_CAPTOP, Z_CAPBAND, Z_RED = zcell(0, 2), zcell(1, 2), zcell(2, 2), zcell(3, 2)
Z_COLLAR, Z_JAW, Z_BELT, Z_METAL = zcell(0, 3), zcell(1, 3), zcell(2, 3), zcell(3, 3)
ZP = {}      # partes guardadas para pintar la textura segun la altura real


def zombie():
    """Zombie de silueta redondeada: gorra de oficial, chaqueta blanca manchada, tirantes,
    brazalete rojo liso, pantalon verde roto, guantes oscuros y pies descalzos."""
    parts, keys = [], []

    def add(key, name, part):
        parts.append(part)
        keys.append(key)
        ZP[name] = part

    for key, s in (("legL", 1), ("legR", -1)):
        cy = 4.6 * s
        add(key, "pants", Loft("z", [(0, 0, cy, 4.7, 4.1), (-5, 0, cy, 4.5, 3.9), (-10.5, 0, cy, 4.0, 3.5),
                                      (-14, 0.3, cy, 3.7, 3.3), (-17, 0.3, cy, 3.4, 3.1)], Z_PANTS, 12))
        add(key, "shin", Loft("z", [(-16.5, 0.2, cy, 3.2, 2.9), (-19, 0.3, cy, 2.5, 2.3),
                                     (-21.5, 0.5, cy, 2.3, 2.2), (-23, 0.8, cy, 2.4, 2.2)], Z_LEG, 10))
        add(key, "foot", Loft("x", [(-3.6, cy, -22.7, 0.5, 0.4), (-3.0, cy, -22.4, 1.9, 1.6), (0, cy, -22.3, 2.4, 1.9),
                                     (4.0, cy, -22.8, 2.5, 1.3), (7.5, cy, -23.3, 2.0, 0.7), (8.5, cy, -23.6, 0.6, 0.4)],
                              Z_LEG, 10))
    add("torso", "torso", Loft("z", [(20.8, 0.4, 0, 2.8, 3.6), (19.6, 0.2, 0, 4.0, 7.2), (18.2, 0, 0, 4.9, 9.4),
                                      (15.5, 0.2, 0, 5.3, 9.3), (11, 0.3, 0, 5.1, 8.5), (6, 0.2, 0, 4.7, 7.7),
                                      (1.5, 0.2, 0, 4.9, 8.0), (-1.5, 0.1, 0, 5.4, 8.8), (-4.5, 0, 0, 5.6, 9.0),
                                      (-4.7, 0, 0, 0.4, 0.4)], Z_TORSO, 18))
    add("torso", "belt", Loft("z", [(4.4, 0.2, 0, 5.15, 8.2), (2.9, 0.2, 0, 5.3, 8.4), (1.3, 0.2, 0, 5.3, 8.4)], Z_BELT, 18))
    add("torso", "buckle", Box(5.2, 6.1, -1.7, 1.7, 1.5, 4.1, Z_METAL))
    add("torso", "collar", Loft("z", [(22.2, 0.4, 0, 3.0, 3.3), (20.9, 0.3, 0, 4.0, 4.6), (19.2, 0.2, 0, 4.9, 6.2)], Z_COLLAR, 14))
    add("torso", "neck", Loft("z", [(24.5, 0.5, 0, 2.1, 2.2), (22, 0.4, 0, 2.3, 2.4), (19.5, 0.2, 0, 2.8, 2.9)], Z_LEG, 10))
    add("headT", "head", Loft("z", [(31.6, 0.3, 0, 2.4, 2.6), (30.4, 0.4, 0, 4.3, 4.3), (28.5, 0.5, 0, 5.0, 4.5),
                                     (26.5, 0.7, 0, 5.0, 4.4), (24.6, 0.9, 0, 4.6, 3.9), (23.2, 1.3, 0, 3.9, 3.3),
                                     (22.3, 1.6, 0, 3.3, 2.8), (22.25, 1.7, 0, 0.4, 0.4)], Z_HEAD, 20))
    add("jawT", "jaw", Loft("z", [(22.5, 1.9, 0, 3.5, 2.9), (20.8, 2.3, 0, 3.4, 2.7), (19.0, 2.6, 0, 2.6, 2.1),
                                   (17.8, 2.9, 0, 1.3, 1.1), (17.6, 2.9, 0, 0.3, 0.3)], Z_JAW, 14))
    add("headT", "capband", Loft("z", [(31.5, 0.3, 0, 5.0, 5.0), (30.5, 0.3, 0, 5.2, 5.2), (29.3, 0.5, 0, 5.2, 5.1)], Z_CAPBAND, 20))
    add("headT", "captop", Loft("z", [(35.1, 0.2, 0, 0.3, 0.3), (34.9, 0.2, 0, 5.6, 5.8), (34.2, 0.1, 0, 6.3, 6.5),
                                       (33.2, 0.1, 0, 5.9, 6.1), (32.2, 0.2, 0, 5.3, 5.4), (31.4, 0.3, 0, 5.2, 5.2)], Z_CAPTOP, 20))
    add("headT", "visor", Loft("x", [(4.8, 0, 30.2, 4.4, 0.7), (7.0, 0, 30.0, 4.0, 0.45), (9.0, 0, 29.8, 2.8, 0.3),
                                      (9.4, 0, 29.8, 0.3, 0.2)], Z_CAPBAND, 12))
    for key, s in (("armL", 1), ("armR", -1)):
        cy, cz = 11.5 * s, 16
        add(key, "sleeve", Loft("x", [(-3.0, cy, cz, 1.0, 1.0), (-2.2, cy, cz, 3.4, 3.4), (0, cy, cz, 4.2, 4.2),
                                       (6, cy, cz, 3.8, 3.8), (13, cy, cz, 3.2, 3.2)], Z_SLEEVE, 12))
        add(key, "forearm", Loft("x", [(12.5, cy, cz, 2.7, 2.7), (16.5, cy, cz, 2.4, 2.4), (20.2, cy, cz, 2.1, 2.1)], Z_ARM, 10))
        add(key, "glove", Loft("x", [(19.8, cy, cz, 2.5, 2.5), (21.6, cy, cz, 2.9, 2.7), (24.2, cy, cz, 3.1, 2.4),
                                      (26.4, cy, cz, 2.7, 1.9), (28.4, cy, cz, 2.0, 1.4), (30.0, cy, cz, 1.3, 0.9),
                                      (30.6, cy, cz, 0.3, 0.3)], Z_GLOVE, 10))
        if s > 0:
            add("armL", "band", Loft("x", [(4.3, cy, cz, 3.95, 3.95), (4.5, cy, cz, 4.5, 4.5), (8.5, cy, cz, 4.35, 4.35),
                                            (8.7, cy, cz, 3.7, 3.7)], Z_RED, 12))

    mesh = Mesh(parts, ZS)
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


# ---- ruido periodico en u (para que no se note la costura al dar la vuelta)
def _vn(x, y, per, seed):
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi

    def h(i, j):
        n = ((i % per) * 374761393 + j * 668265263 + seed * 144665) & 0xFFFFFFFF
        n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0
    sx, sy = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    return (h(xi, yi) * (1 - sx) + h(xi + 1, yi) * sx) * (1 - sy) + (h(xi, yi + 1) * (1 - sx) + h(xi + 1, yi + 1) * sx) * sy


def pn(fu, fv, px, sy, seed=0):
    tot = 0.0
    for k, a in enumerate((0.55, 0.3, 0.15)):
        m = 1 << k
        tot += a * _vn(fu * px * m, fv * sy * m, px * m, seed + k)
    return tot


def sstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def paint(z, W, r, fn, rng, grain=5):
    u0, v0, u1, v1 = r
    for y in range(max(0, v0 - 1), min(W - 1, v1 + 1) + 1):
        for x in range(max(0, u0 - 1), min(W - 1, u1 + 1) + 1):
            fu = max(0.0, min(1.0, (x - u0) / (u1 - u0)))
            fv = max(0.0, min(1.0, (y - v0) / (v1 - v0)))
            c = fn(fu, fv)
            k = rng.uniform(-grain, grain)
            z[y * W + x] = tuple(max(0, min(255, int(v + k))) for v in c)


WHITE, DIRT = (212, 207, 194), (168, 152, 116)
BLOOD, DRY = (134, 36, 26), (86, 30, 24)
STRAP, STRAP_E = (74, 50, 34), (46, 30, 20)


def make_zombie_texture(outdir):
    zombie()                       # rellena ZP con las partes
    rng = random.Random(7)
    W = ZS
    z = [(0, 0, 0)] * (W * W)
    TH = lambda fu: -math.pi + 2 * math.pi * fu

    def stain(c, fu, fv, px=5, sy=4, seed=7, thr=0.60, amt=0.92):
        thr += 0.09
        c = mix(c, BLOOD, amt * sstep((pn(fu, fv, px, sy, seed) - thr) / 0.07))
        return mix(c, DRY, 0.8 * sstep((pn(fu, fv, px + 3, sy + 3, seed + 9) - (thr + 0.1)) / 0.06))

    def torso(fu, fv):
        zz, th = ZP["torso"].pos_at(fv), TH(fu)
        a = abs(th)
        c = mix(WHITE, DIRT, 0.55 * pn(fu, fv, 6, 5, 1))
        c = mix(c, (186, 180, 166), 0.35 * pn(fu, fv, 24, 3, 2))
        if zz > 11.0:                                         # V del cuello con solapas verdes
            vw = 0.15 + 0.5 * (zz - 11) / 9
            if a < vw:
                c = mix((126, 127, 114), (96, 100, 92), pn(fu, fv, 10, 6, 3))
            elif a < vw + 0.32:
                c = mix((66, 84, 60), (48, 62, 44), pn(fu, fv, 12, 6, 4))
        if 4.0 < zz < 19.0 and abs(a - 0.52) < 0.075:        # tirantes delanteros
            c = STRAP if abs(a - 0.52) < 0.055 else STRAP_E
        if 5.0 < zz < 18.5:                                   # tirantes en Y por la espalda
            if abs((math.pi - a) - (0.12 + 0.9 * (zz - 5) / 13.5)) < 0.075:
                c = STRAP
        for zb in (10.2, 6.8):                                # botones
            if a < 0.07 and abs(zz - zb) < 0.5:
                c = (168, 164, 148)
        if 8.5 < zz < 13.2 and 0.95 < a < 1.5:                # bolsillos
            if min(abs(zz - 8.5), abs(zz - 13.2), abs(a - 0.95), abs(a - 1.5)) < 0.12:
                c = (150, 144, 130)
        if zz < -2.4 - 0.9 * math.sin(th * 7):                # faldon rasgado
            c = mix(c, (96, 86, 72), 0.65)
        return stain(c, fu, fv)

    def sleeve(fu, fv):
        c = mix(WHITE, DIRT, 0.5 * pn(fu, fv, 5, 4, 11))
        c = mix(c, (186, 180, 166), 0.3 * pn(fu, fv, 16, 3, 12))
        if fv > 0.88 + 0.06 * math.sin(fu * 40):              # manga rota
            c = mix((150, 146, 128), (110, 100, 86), pn(fu, fv, 10, 6, 13))
        return stain(c, fu, fv, 4, 4, 14, 0.58)

    def pants(fu, fv):
        c = mix((92, 104, 72), (60, 68, 48), pn(fu, fv, 6, 5, 21))
        c = mix(c, (122, 130, 96), 0.5 * sstep((pn(fu, fv, 9, 7, 22) - 0.6) / 0.1))
        if fv > 0.80 + 0.1 * (math.sin(fu * 50) * 0.5 + 0.5):   # bordes rotos que dejan ver la piel
            c = mix((158, 140, 114), (120, 40, 30), 0.35 * pn(fu, fv, 8, 6, 23))
        if pn(fu, fv, 5, 5, 24) > 0.74:                       # desgarros con herida
            c = mix((150, 136, 114), BLOOD, 0.7 * sstep((pn(fu, fv, 9, 9, 25) - 0.5) / 0.15))
        return stain(c, fu, fv, 4, 4, 26, 0.66, 0.8)

    def leg(fu, fv):
        c = mix((164, 144, 118), (96, 82, 62), pn(fu, fv, 8, 8, 31))
        return stain(c, fu, fv, 4, 4, 32, 0.68, 0.75)

    def arm(fu, fv):
        c = mix((146, 146, 128), (98, 108, 98), 0.7 * pn(fu, fv, 8, 6, 41))
        return stain(c, fu, fv, 4, 4, 42, 0.52, 0.9)

    def glove(fu, fv):
        c = mix((50, 42, 38), (88, 76, 68), 0.8 * pn(fu, fv, 8, 8, 51))
        if int(fv * 9) in (3, 6) and 0.2 < fu < 0.8:
            c = mix(c, (30, 24, 22), 0.6)
        return stain(c, fu, fv, 4, 4, 52, 0.74, 0.7)

    def captop(fu, fv):
        c = mix((86, 92, 78), (58, 62, 50), pn(fu, fv, 8, 6, 61))
        return stain(c, fu, fv, 4, 4, 62, 0.74, 0.7)

    def capband(fu, fv):
        return mix((30, 28, 26), (62, 58, 54), 0.7 * pn(fu, fv, 12, 4, 71))

    def red(fu, fv):
        c = mix((160, 32, 30), (122, 22, 22), 0.8 * pn(fu, fv, 10, 4, 81))
        return mix(c, DRY, 0.8 * sstep((pn(fu, fv, 5, 3, 82) - 0.6) / 0.08))

    def collar(fu, fv):
        return stain(mix((66, 84, 60), (46, 60, 44), pn(fu, fv, 10, 4, 91)), fu, fv, 4, 3, 92, 0.72, 0.8)

    def belt(fu, fv):
        return mix((70, 48, 34), (40, 28, 20), 0.8 * pn(fu, fv, 14, 3, 101))

    def metal(fu, fv):
        return mix((182, 168, 120), (130, 118, 82), pn(fu, fv, 3, 3, 111))

    def jaw(fu, fv):
        th = TH(fu)
        a = abs(th)
        c = mix((150, 150, 136), (110, 118, 108), pn(fu, fv, 8, 5, 121))
        if fv < 0.34 and a < 1.5:                             # dientes inferiores
            sep = (a / 0.11) % 1.0
            c = mix((226, 218, 190), (120, 96, 76), 0.8 if sep < 0.14 else 0.1 * pn(fu, fv, 20, 20, 122))
            if fv < 0.07:
                c = (78, 14, 12)
        elif fv < 0.55 and a < 1.6:
            c = mix((130, 30, 26), (70, 12, 10), pn(fu, fv, 10, 6, 123))
        return stain(c, fu, fv, 5, 4, 124, 0.62, 0.9)

    def head(fu, fv):
        zz, th = ZP["head"].pos_at(fv), TH(fu)
        a, sg = abs(th), (1 if th >= 0 else -1)
        c = mix((152, 153, 140), (104, 114, 106), 0.9 * pn(fu, fv, 10, 7, 131))      # piel con venas
        if a < 1.1:
            d = (a - 0.52) ** 2 / 0.30 ** 2 + (zz - 26.9) ** 2 / 1.25 ** 2          # cuenca del ojo
            if d < 1.0:
                c = mix((38, 30, 28), c, sstep((d - 0.55) / 0.45) * 0.8)
            de = (a - 0.52) ** 2 / 0.17 ** 2 + (zz - 26.9) ** 2 / 0.55 ** 2         # ojo brillante
            if de < 1.0:
                c = mix((255, 236, 120), (236, 150, 30), sstep(de - 0.3))
            if abs(zz - 28.4) < 0.35 and 0.25 < a < 0.85:                           # ceja
                c = mix(c, (90, 90, 80), 0.6)
            if a < 0.17 and 23.6 < zz < 26.0:                                       # nariz
                c = mix(c, (96, 90, 80), 0.6)
            for sx in (-1, 1):
                if abs(a * 1 - 0.1) < 0.045 and abs(zz - 24.0) < 0.25:              # fosas nasales
                    c = (44, 26, 24)
            d2 = (a - 0.85) ** 2 / 0.25 ** 2 + (zz - 24.3) ** 2 / 1.4 ** 2          # mejillas hundidas
            if d2 < 1.0:
                c = mix(c, (112, 114, 104), 0.5 * (1 - d2))
        if zz < 23.7 and a < 0.75:                                                  # boca abierta
            if zz > 22.75:
                sep = (a / 0.1) % 1.0
                c = mix((228, 220, 192), (96, 70, 56), 0.9 if sep < 0.12 else 0.0)  # dientes superiores
            else:
                c = (74, 14, 12)
        if zz < 23.6 and a < 0.75 and pn(fu * 3 % 1, fv, 6, 6, 133) > 0.5:          # sangre en la barbilla
            c = mix(c, BLOOD, 0.8)
        return stain(c, fu, fv, 5, 4, 134, 0.7, 0.85)

    for r, fn, g in ((Z_TORSO, torso, 4), (Z_SLEEVE, sleeve, 4), (Z_PANTS, pants, 4), (Z_LEG, leg, 4), (Z_ARM, arm, 4),
                     (Z_GLOVE, glove, 4), (Z_CAPTOP, captop, 3), (Z_CAPBAND, capband, 3), (Z_RED, red, 4),
                     (Z_COLLAR, collar, 4), (Z_BELT, belt, 3), (Z_METAL, metal, 3), (Z_JAW, jaw, 4), (Z_HEAD, head, 3)):
        paint(z, W, r, fn, rng, g)
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
