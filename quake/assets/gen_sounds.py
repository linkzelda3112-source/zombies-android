#!/usr/bin/env python3
"""Genera los sonidos del juego (WAV 16 bit mono 22050 Hz) por sintesis."""
import math, random, struct, sys, os, wave

RATE = 22050


def write_wav(path, samples):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    peak = max(1e-9, max(abs(s) for s in samples))
    scale = 0.9 / peak * 32767
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", max(-32767, min(32767, int(s * scale)))) for s in samples))


def n_samples(sec):
    return int(sec * RATE)


def lowpass(x, k):
    out, y = [], 0.0
    for s in x:
        y += k * (s - y)
        out.append(y)
    return out


def noise(rng, n):
    return [rng.uniform(-1, 1) for _ in range(n)]


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, s in enumerate(t):
            out[i] += s
    return out


def delay(x, sec, gain=1.0):
    return [0.0] * n_samples(sec) + [s * gain for s in x]


def gunshot(rng, dur, thump_hz, thump_decay, crack_decay, crack_lp, boom=1.0, tail=0.0):
    n = n_samples(dur)
    nz = lowpass(noise(rng, n), crack_lp)
    out = []
    for i in range(n):
        t = i / RATE
        crack = nz[i] * math.exp(-t * crack_decay)
        thump = math.sin(2 * math.pi * thump_hz * t * (1 - 0.5 * t)) * math.exp(-t * thump_decay) * boom
        out.append(crack * 1.4 + thump)
    if tail:
        verb = lowpass(noise(rng, n_samples(tail)), 0.05)
        verb = [v * math.exp(-i / RATE * 4) * 0.25 for i, v in enumerate(verb)]
        out = mix(out, delay(verb, 0.03))
    return out


def click(rng, freq=2200, dur=0.03):
    n = n_samples(dur)
    return [math.sin(2 * math.pi * freq * i / RATE) * math.exp(-i / RATE * 140) + rng.uniform(-0.3, 0.3) * math.exp(-i / RATE * 200) for i in range(n)]


def groan(rng, dur, f0, f1, vib=5.0, rough=0.5):
    n = n_samples(dur)
    out, ph = [], 0.0
    for i in range(n):
        t = i / RATE
        f = f0 + (f1 - f0) * (t / dur) + math.sin(2 * math.pi * vib * t) * 6
        ph += 2 * math.pi * f / RATE
        # onda tipo diente de sierra suavizada = voz ronca
        saw = 2 * ((ph / (2 * math.pi)) % 1) - 1
        pulse = saw * (0.6 + 0.4 * math.sin(2 * math.pi * 23 * t))
        env = min(1, t * 12) * min(1, (dur - t) * 6)
        out.append(pulse * env)
    out = lowpass(out, 0.14)
    nz = lowpass(noise(rng, n), 0.25)
    return [o * 1.8 + nz[i] * rough * 0.5 * min(1, i / 2000) for i, o in enumerate(out)]


def tone(freq, dur, decay, harmonics=((1, 1.0),)):
    n = n_samples(dur)
    return [sum(a * math.sin(2 * math.pi * freq * h * i / RATE) for h, a in harmonics) * math.exp(-i / RATE * decay) for i in range(n)]


def main(outdir):
    rng = random.Random(7)
    s = lambda name, data: write_wav(os.path.join(outdir, "sound", name), data)

    s("weapons/pistol.wav", gunshot(rng, 0.30, 110, 22, 38, 0.55, 1.0, 0.25))
    s("weapons/smg.wav", gunshot(rng, 0.16, 140, 40, 55, 0.7, 0.7, 0.1))
    s("weapons/shotgun.wav", gunshot(rng, 0.55, 70, 11, 16, 0.35, 1.6, 0.45))
    s("weapons/rifle.wav", gunshot(rng, 0.45, 90, 15, 24, 0.5, 1.4, 0.4))

    # recarga: cargador fuera, cargador dentro, cerrojo
    slide = [x * 0.5 for x in lowpass(noise(rng, n_samples(0.12)), 0.3)]
    slide = [v * math.sin(math.pi * i / len(slide)) for i, v in enumerate(slide)]
    s("weapons/reload.wav", mix(click(rng, 1500), delay(click(rng, 2400), 0.55), delay(slide, 0.85), delay(click(rng, 3000, 0.04), 1.0)))
    s("weapons/empty.wav", click(rng, 1800, 0.05))

    s("zombie/groan1.wav", groan(rng, 1.1, 85, 62))
    s("zombie/groan2.wav", groan(rng, 0.8, 110, 70, 7))
    s("zombie/groan3.wav", groan(rng, 1.3, 70, 90, 4))
    swing = lowpass(noise(rng, n_samples(0.35)), 0.12)
    swing = [v * math.sin(math.pi * i / len(swing)) * 1.5 for i, v in enumerate(swing)]
    s("zombie/hit.wav", mix(swing, delay(tone(70, 0.2, 18), 0.18, 1.2)))
    s("zombie/pain.wav", groan(rng, 0.35, 150, 110, 9, 0.9))
    s("zombie/die.wav", groan(rng, 0.9, 120, 40, 6, 0.8))
    s("player/pain.wav", groan(rng, 0.28, 210, 150, 8, 0.4))
    s("player/death.wav", groan(rng, 1.0, 190, 60, 4, 0.5))

    s("misc/buy.wav", mix(tone(880, 0.4, 9, ((1, 1), (2, 0.4))), delay(tone(1320, 0.55, 7, ((1, 1), (2, 0.3))), 0.11)))
    nb = n_samples(0.3)
    s("misc/nobuy.wav", [(1 if math.sin(2 * math.pi * 110 * i / RATE) > 0 else -1) * 0.5 * math.exp(-i / RATE * 6) for i in range(nb)])

    # inicio de ronda: acorde grave inquietante que crece
    n = n_samples(2.8)
    rs = []
    for i in range(n):
        t = i / RATE
        env = math.sin(math.pi * min(1, t / 2.8)) ** 1.5
        v = math.sin(2 * math.pi * 55 * t) + 0.8 * math.sin(2 * math.pi * 58.3 * t) + 0.5 * math.sin(2 * math.pi * 82.4 * t + 0.4 * math.sin(2 * math.pi * 3 * t))
        rs.append(v * env * 0.6)
    s("misc/round_start.wav", mix(rs, delay(tone(220, 1.4, 2.0, ((1, 1), (3, 0.3))), 0.1, 0.15)))
    s("misc/round_end.wav", mix(tone(392, 1.6, 2.5, ((1, 1), (2, 0.5))), delay(tone(330, 1.6, 2.5, ((1, 1), (2, 0.5))), 0.35), delay(tone(247, 2.2, 2.0, ((1, 1), (2, 0.4))), 0.7)))
    s("misc/gameover.wav", mix(tone(196, 3.0, 1.2, ((1, 1), (2, 0.5), (3, 0.2))), delay(tone(185, 3.0, 1.2, ((1, 1), (2, 0.5))), 0.5), delay(tone(98, 3.0, 1.0, ((1, 1), (2, 0.6))), 1.0)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build/pak")
