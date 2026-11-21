"""Sonido provisional de las esposas (tanda A, novena: la detención): dos trinquetes metálicos seguidos (el chasquido del
cierre y la cremallera de dientes de la argolla) y un tintineo de la cadena. Sintetizado sin bancos de sonido ni
licencias, en Python sin numpy (también lo corre el Python de Unreal).
Uso: python tools/sonido/esposas.py  -> assets/unreal/sonidos/esposas.wav (lo importa tools/unreal/sonidos.py)."""
import math, os, random, struct, wave

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets', 'unreal', 'sonidos')
rnd = random.Random(1983)


def clic(x, o, f, dec, a):
    """golpe metálico corto en la muestra o: dos senos inarmónicos y un soplo de ruido, que decaen"""
    for i in range(int(dec * 8 * SR)):
        if o + i >= len(x):
            break
        t = i / SR
        e = math.exp(-t / dec)
        x[o + i] += a * e * (math.sin(2 * math.pi * f * t) + 0.6 * math.sin(2 * math.pi * f * 2.76 * t) + 0.35 * math.sin(2 * math.pi * f * 5.4 * t))
        x[o + i] += a * 0.7 * math.exp(-t / (dec / 5)) * (rnd.random() * 2 - 1)


def esposas():
    n = int(0.95 * SR)
    x = [0.0] * n
    # primera argolla: cierre seco y 7 dientes de trinquete cada vez más rápidos
    o = 0
    clic(x, o, 3100, 0.012, 1.0)
    for k in range(7):
        o += int((0.028 - k * 0.002) * SR)
        clic(x, o, 2600 + 90 * k, 0.006, 0.45)
    # segunda argolla, un poco más grave
    o = int(0.42 * SR)
    clic(x, o, 2800, 0.012, 0.9)
    for k in range(6):
        o += int((0.026 - k * 0.002) * SR)
        clic(x, o, 2400 + 80 * k, 0.006, 0.4)
    # la cadena que tintinea al soltarla
    for d in (0.66, 0.71, 0.79):
        clic(x, int(d * SR), 4300 + rnd.random() * 600, 0.02, 0.18)
    pico = max(abs(v) for v in x) or 1.0
    return [v / pico * 0.75 for v in x]


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    x = esposas()
    with wave.open(os.path.join(OUT, 'esposas.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b''.join(struct.pack('<h', int(v * 32767)) for v in x))
    print('esposas', round(len(x) / SR, 2), 's')
