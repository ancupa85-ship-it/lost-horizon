"""Genera los sonidos de Tarsis (pasos, piedra, dardo, viento, lluvia, radio, generador) como .wav en assets/unreal/sonidos.

Todo sintetizado con numpy (ruido filtrado y senos que decaen): sin bancos de sonidos ni licencias.
Uso: python3 tools/sonido/generar_sonidos.py
"""
import os, wave
import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets', 'unreal', 'sonidos')
rng = np.random.default_rng(7)

def lp(x, a):            # paso bajo de un polo (a cerca de 1 = más grave)
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc = a * acc + (1 - a) * v; y[i] = acc
    return y

def hp(x, a):
    return x - lp(x, a)

def env(n, att, dec):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(att, 1e-4)) * np.exp(-t / dec)
    return e

def save(name, x, peak=0.8):
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name + '.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())
    print(name, round(len(x) / SR, 2), 's')

def grava(k):
    # crujido: muchos chasquidos pequeños de piedrecitas en ~150 ms
    n = int(0.22 * SR); x = np.zeros(n)
    for _ in range(40 + 10 * k):
        p = int(abs(rng.normal(0.05, 0.035)) * SR)
        if p >= n - 400: continue
        m = int(rng.uniform(60, 300)); b = rng.normal(0, 1, m) * env(m, 0.0003, rng.uniform(0.0008, 0.003))
        x[p:p + m] += b * rng.uniform(0.3, 1.0)
    x = hp(x, 0.6) + 0.25 * lp(rng.normal(0, 1, n), 0.97) * env(n, 0.005, 0.04)
    return x

def cemento(k):
    n = int(0.16 * SR); t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * (90 + 15 * k) * t) * env(n, 0.002, 0.025)
    scuff = hp(rng.normal(0, 1, n), 0.8) * env(n, 0.001, 0.012) * 0.5
    return thump + scuff

def piedra():
    n = int(0.5 * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for d, a in ((0.0, 1.0), (0.11, 0.45), (0.19, 0.2)):   # golpe y dos botes
        o = int(d * SR); m = n - o; tt = t[:m]
        hit = (np.sin(2 * np.pi * 2300 * tt) + 0.7 * np.sin(2 * np.pi * 3450 * tt) + 0.4 * np.sin(2 * np.pi * 5200 * tt)) * np.exp(-tt / 0.018)
        hit += rng.normal(0, 1, m) * np.exp(-tt / 0.006) * 0.8
        x[o:] += a * hit
    return x

def dardo():
    n = int(0.25 * SR)
    x = hp(lp(rng.normal(0, 1, n), 0.5), 0.9) * env(n, 0.004, 0.05)
    t = np.arange(n) / SR
    x += 0.3 * np.sin(2 * np.pi * 180 * t) * env(n, 0.001, 0.01)
    return x

def bucle(x, fade=1.0):
    # se funde el final con el principio para que el bucle no tenga corte
    f = int(fade * SR); a = np.linspace(0, 1, f)
    y = x[f:].copy(); y[-f:] = y[-f:] * (1 - a) + x[:f] * a
    return y

def viento(sec=12):
    n = int((sec + 1) * SR)
    b = np.cumsum(rng.normal(0, 1, n)); b -= lp(b, 0.9995)          # ruido marrón sin deriva
    t = np.arange(n) / SR
    g = 0.55 + 0.3 * np.sin(2 * np.pi * t / 5.3) + 0.15 * np.sin(2 * np.pi * t / 2.1 + 1)   # rachas
    whistle = lp(rng.normal(0, 1, n), 0.995) * 0.0
    return bucle(lp(b, 0.7) * g + whistle)

def lluvia(sec=10):
    n = int((sec + 1) * SR)
    x = hp(rng.normal(0, 1, n), 0.4) * 0.25 + lp(rng.normal(0, 1, n), 0.9) * 0.6
    for _ in range(sec * 120):                                        # gotas sueltas
        p = int(rng.uniform(0, n - 600)); m = int(rng.uniform(100, 500))
        x[p:p + m] += rng.normal(0, 1, m) * env(m, 0.0002, 0.002) * rng.uniform(0.5, 2.0)
    return bucle(x)

def radio():
    # chasquido de radio: ruido filtrado a banda de voz que entra y sale, con un pitido corto al final
    n = int(0.9 * SR); t = np.arange(n) / SR
    x = hp(lp(rng.normal(0, 1, n), 0.6), 0.97)
    g = np.ones(n); g[:int(0.03 * SR)] = np.linspace(0, 1, int(0.03 * SR)); g[int(0.7 * SR):] = 0
    x = x * g * (0.6 + 0.4 * (rng.random(n) > 0.02))
    b = int(0.72 * SR); m = int(0.08 * SR)
    x[b:b + m] += 0.5 * np.sin(2 * np.pi * 1200 * t[:m]) * env(m, 0.002, 0.03)
    return x

def generador(sec=6):
    # motor diésel al ralentí: zumbido de 50 Hz con armónicos, golpeteo de 12,5 Hz y ruido mecánico
    n = int((sec + 1) * SR); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t + i) for i, (f, a) in enumerate(((50, 1.0), (100, 0.6), (150, 0.35), (200, 0.2), (300, 0.08))))
    x *= 0.75 + 0.25 * np.sin(2 * np.pi * 12.5 * t) ** 2
    x += lp(rng.normal(0, 1, n), 0.8) * 0.25
    return bucle(x)

if __name__ == '__main__':
    for k in range(3):
        save('paso_grava_%d' % (k + 1), grava(k), 0.7)
        save('paso_cemento_%d' % (k + 1), cemento(k), 0.6)
    save('piedra', piedra())
    save('dardo', dardo(), 0.6)
    save('viento', viento(), 0.5)
    save('lluvia', lluvia(), 0.5)
    save('radio', radio(), 0.6)
    save('generador', generador(), 0.5)
