"""Tanda N: sonidos del peligro de los tiros y de los golpes (sintetizados con numpy, sin bancos ni licencias).

- silbido_1..3: la bala que pasa cerca (banda de ruido que sube y baja con un chasquido delante, ~0,3 s).
- impacto_tierra_1..3, impacto_metal_1..3, impacto_madera_1..3: donde da el tiro que falla.
- golpe_seco_1..2: el remate cuerpo a cuerpo (golpe grave y un crujido de tela).
Uso: python tools/sonido/generar_peligro.py   (cualquier Python con numpy; el de Blender vale)
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generar_sonidos import SR, lp, hp, env, save, rng


def silbido(k):
    n = int(0.34 * SR)
    t = np.arange(n) / SR
    ruido = rng.normal(0, 1, n)
    # el paso de la bala: una banda que sube de tono y cae (Doppler), corta y seca
    centro = 0.12 + 0.02 * k
    forma = np.exp(-((t - centro) / 0.045) ** 2)
    banda = hp(lp(ruido, 0.55), 0.985)
    tono = np.sin(2 * np.pi * np.cumsum(2600 - 1600 * np.tanh((t - centro) * 40)) / SR)
    chasquido = np.zeros(n)
    i = int((centro - 0.03) * SR)
    chasquido[i:i + 200] = rng.normal(0, 1, 200) * np.exp(-np.arange(200) / 30)
    return banda * forma * 0.8 + tono * forma * 0.25 + chasquido * 0.9


def impacto_tierra(k):
    n = int(0.45 * SR)
    golpe = lp(rng.normal(0, 1, n), 0.93) * env(n, 0.001, 0.05)
    tierra = lp(rng.normal(0, 1, n), 0.6) * env(n, 0.004, 0.16 + 0.03 * k) * 0.5   # la tierra que cae
    return golpe * 1.4 + tierra


def impacto_metal(k):
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    golpe = hp(rng.normal(0, 1, n), 0.7) * env(n, 0.0005, 0.012)
    f = 1800 + 500 * k
    zumbido = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.7 * t)) * env(n, 0.001, 0.12)
    # el rebote: un silbido que baja
    reb = np.sin(2 * np.pi * np.cumsum(3200 - 1400 * t / t[-1]) / SR) * np.exp(-((t - 0.08) / 0.12) ** 2) * 0.35
    return golpe * 1.2 + zumbido * 0.5 + reb


def impacto_madera(k):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    golpe = lp(rng.normal(0, 1, n), 0.8) * env(n, 0.0008, 0.03)
    cuerpo = np.sin(2 * np.pi * (380 + 60 * k) * t) * env(n, 0.001, 0.05) * 0.6
    astillas = hp(rng.normal(0, 1, n), 0.9) * env(n, 0.002, 0.06) * 0.3
    return golpe * 1.3 + cuerpo + astillas


def golpe_seco(k):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    grave = np.sin(2 * np.pi * (70 + 15 * k) * t) * env(n, 0.002, 0.09)
    carne = lp(rng.normal(0, 1, n), 0.9) * env(n, 0.001, 0.04)
    tela = hp(rng.normal(0, 1, n), 0.95) * env(n, 0.01, 0.12) * 0.25
    return grave * 1.2 + carne * 1.0 + tela


if __name__ == '__main__':
    for k in range(1, 4):
        save('silbido_%d' % k, silbido(k), 0.7)
        save('impacto_tierra_%d' % k, impacto_tierra(k), 0.8)
        save('impacto_metal_%d' % k, impacto_metal(k), 0.7)
        save('impacto_madera_%d' % k, impacto_madera(k), 0.8)
    for k in range(1, 3):
        save('golpe_seco_%d' % k, golpe_seco(k), 0.9)
