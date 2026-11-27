"""Tanda P: el sonido del cuerpo a cuerpo en capas (sintetizado con numpy, sin bancos ni licencias; provisional).

Cada golpe suena con 3 a 5 capas a la vez, elegidas al azar entre variantes (ATarsisDirector::PlayImpact):
- golpe_grave_1..3: el peso del golpe (seno de 55-80 Hz que cae de tono, con ruido grave), lo que se siente en el pecho.
- golpe_medio_1..3: la carne y la tela (ruido en banda de 250-1500 Hz, muy corto).
- golpe_chasquido_1..3: el corte agudo del contacto (chasquido de 2-6 kHz, 15-30 ms).
- golpe_pared_1..3: la capa de mas contra el entorno (golpe sordo con la resonancia de un muro o un contenedor).
- esfuerzo_cuttlas_1..3, dolor_cuttlas_1..2: el gemido de Cuttlas al golpear y al recibir.
- esfuerzo_guardia_1..3, dolor_guardia_1..3: lo mismo de los guardias (mas graves).
Las voces son sintesis de formantes (pulsos de glotis por filtros de vocal), sin palabras: gemidos cortos.
Uso: python tools/sonido/generar_golpes.py   (cualquier Python con numpy; el de Blender vale)
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generar_sonidos import SR, lp, hp, env, save

rng = np.random.default_rng(23)


def t_of(seg):
    n = int(seg * SR)
    return n, np.arange(n) / SR


def grave(k):
    n, t = t_of(0.32)
    f0 = 80 - 8 * k
    f = f0 * (1.0 + 0.9 * np.exp(-t / 0.03))         # cae de tono: el pecho que encaja
    fase = 2 * np.pi * np.cumsum(f) / SR
    cuerpo = np.sin(fase) * np.exp(-t / (0.07 + 0.015 * k))
    ruido = lp(rng.normal(0, 1, n), 0.97) * np.exp(-t / 0.05) * 1.6
    golpe = cuerpo + ruido * 0.6
    golpe[:int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return np.tanh(golpe * 1.8)


def medio(k):
    n, t = t_of(0.12)
    r = rng.normal(0, 1, n)
    banda = hp(lp(r, 0.55 + 0.08 * k), 0.93)
    tela = hp(lp(rng.normal(0, 1, n), 0.35), 0.8) * np.exp(-t / 0.03) * 0.5
    return banda * env(n, 0.0008, 0.022 + 0.006 * k) + tela


def chasquido(k):
    n, t = t_of(0.06)
    r = hp(rng.normal(0, 1, n), 0.6 - 0.1 * k)
    c = r * np.exp(-t / (0.006 + 0.003 * k))
    tono = np.sin(2 * np.pi * (2400 + 900 * k) * t) * np.exp(-t / 0.01) * 0.4
    return c + tono


def pared(k):
    n, t = t_of(0.45)
    golpe = lp(rng.normal(0, 1, n), 0.9) * np.exp(-t / 0.04)
    modos = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / d) * a
                for f, d, a in ((110 + 20 * k, 0.12, 0.8), (260 + 35 * k, 0.07, 0.5), (590 + 60 * k, 0.05, 0.3)))
    return np.tanh((golpe + modos * 0.7) * 1.5)


def formante(x, f, ancho):
    # resonador de dos polos (filtro de formante)
    r = np.exp(-np.pi * ancho / SR)
    a1, a2 = -2 * r * np.cos(2 * np.pi * f / SR), r * r
    y = np.zeros_like(x)
    for i in range(len(x)):
        y[i] = x[i] - a1 * (y[i - 1] if i > 0 else 0) - a2 * (y[i - 2] if i > 1 else 0)
    return y


def gemido(f0, dur, vocal, subida, aliento, k):
    n, t = t_of(dur)
    # tono: arranca, sube o baja un poco y cae al final
    tono = f0 * (1 + subida * np.sin(np.pi * np.clip(t / dur, 0, 1))) * (1 + 0.02 * rng.normal(0, 1, n).cumsum() / np.sqrt(np.arange(1, n + 1)))
    fase = np.cumsum(tono) / SR
    pulsos = (np.mod(fase, 1.0) < 0.08).astype(float) - 0.08   # tren de pulsos de glotis
    pulsos += rng.normal(0, aliento, n)                        # aire
    voz = sum(formante(pulsos, f, b) * g for f, b, g in vocal)
    e = np.minimum(1, t / 0.015) * np.exp(-np.maximum(0, t - dur * 0.35) / (dur * 0.3))
    v = voz * e
    return np.tanh(v / (np.max(np.abs(v)) + 1e-9) * 1.2 * (1 + 0.1 * k))   # apenas saturado: voz, no zumbido


# vocales: (frecuencia, ancho de banda, ganancia) de los tres primeros formantes
UH = ((500, 90, 1.0), (1000, 110, 0.5), (2400, 160, 0.2))
AH = ((750, 100, 1.0), (1200, 120, 0.6), (2500, 170, 0.25))
EH = ((560, 90, 1.0), (1700, 120, 0.5), (2500, 170, 0.25))

if __name__ == '__main__':
    for k in range(3):
        save('golpe_grave_%d' % (k + 1), grave(k), 0.9)
        save('golpe_medio_%d' % (k + 1), medio(k), 0.7)
        save('golpe_chasquido_%d' % (k + 1), chasquido(k), 0.6)
        save('golpe_pared_%d' % (k + 1), pared(k), 0.85)
        save('esfuerzo_cuttlas_%d' % (k + 1), gemido(128 + 8 * k, 0.22 + 0.04 * k, (UH, EH, AH)[k], 0.12, 0.35, k), 0.7)
        save('esfuerzo_guardia_%d' % (k + 1), gemido(98 + 6 * k, 0.24 + 0.05 * k, (AH, UH, AH)[k], 0.15, 0.4, k), 0.75)
        save('dolor_guardia_%d' % (k + 1), gemido(110 + 10 * k, 0.32 + 0.06 * k, (AH, EH, UH)[k], -0.18, 0.5, k), 0.75)
    for k in range(2):
        save('dolor_cuttlas_%d' % (k + 1), gemido(140 + 12 * k, 0.3 + 0.05 * k, (EH, AH)[k], -0.2, 0.45, k), 0.7)
