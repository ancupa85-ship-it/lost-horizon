"""Genera los sonidos de Tarsis (pasos en grava, cemento, metal, madera y hierba, piedra, dardo, puertas, teclado, objetos,\nreja, barrera, viento, lluvia, grillos, rumor lejano, radio, generador y las tres capas de música) como .wav en assets/unreal/sonidos.

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

def metal(k):
    # sobre chapa (tejados, contenedores, pasarelas): golpe sordo y un timbre metálico corto
    n = int(0.32 * SR); t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * (70 + 10 * k) * t) * env(n, 0.002, 0.03)
    ring = sum(a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f, a in
               ((410 + 37 * k, 0.5), (1130 + 90 * k, 0.35), (2470 - 60 * k, 0.2), (3310, 0.12))) * env(n, 0.001, 0.08)
    scuff = hp(rng.normal(0, 1, n), 0.7) * env(n, 0.001, 0.015) * 0.4
    return thump + 0.55 * ring + scuff

def madera(k):
    # tablas (plataformas de las torres, suelos de madera): golpe hueco y un crujido breve
    n = int(0.24 * SR); t = np.arange(n) / SR
    knock = (np.sin(2 * np.pi * (180 + 20 * k) * t) + 0.6 * np.sin(2 * np.pi * (390 + 30 * k) * t)) * env(n, 0.001, 0.035)
    f = 520 + 160 * k + 90 * np.sin(2 * np.pi * 23 * t)
    creak = 0.18 * np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(n, 0.03, 0.05)
    scuff = lp(rng.normal(0, 1, n), 0.5) * env(n, 0.001, 0.02) * 0.5
    return knock + lp(creak, 0.6) + scuff

def hierba(k):
    # hierba y tierra blanda: roce de hojas, casi sin golpe
    n = int(0.3 * SR); x = np.zeros(n); t = np.arange(n) / SR
    for _ in range(25 + 5 * k):
        p = int(abs(rng.normal(0.06, 0.04)) * SR)
        if p >= n - 800: continue
        m = int(rng.uniform(300, 800)); x[p:p + m] += hp(rng.normal(0, 1, m), 0.85) * env(m, 0.004, 0.012) * rng.uniform(0.3, 1.0)
    thump = np.sin(2 * np.pi * 60 * t) * env(n, 0.004, 0.03) * 0.35
    return x + thump

def golpe(n, f, dec, a=1.0):
    t = np.arange(n) / SR
    return a * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.7 * t)) * env(n, 0.001, dec) + a * 0.6 * rng.normal(0, 1, n) * env(n, 0.0005, dec / 6)

def puerta_madera():
    # bisagra que chirría al abrir y el golpe de la hoja contra el tope
    n = int(1.1 * SR); t = np.arange(n) / SR
    f = 260 + 120 * np.sin(2 * np.pi * 0.9 * t) + 25 * rng.normal(0, 1, n).cumsum() / np.sqrt(n)
    creak = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * (rng.random(n) > 0.3)
    creak = lp(creak, 0.75) * np.clip(np.sin(np.pi * t / 0.85), 0, 1) * 0.5
    x = creak.copy()
    o = int(0.88 * SR); x[o:] += golpe(n - o, 95, 0.09)
    return x

def puerta_blindada():
    # cerrojo de la puerta blindada del archivo: dos chasquidos metálicos, golpe grave y un siseo de goma
    n = int(1.0 * SR); x = np.zeros(n)
    for d, f in ((0.0, 2100), (0.09, 1600)):
        o = int(d * SR); x[o:] += golpe(n - o, f, 0.025, 0.7)
    o = int(0.25 * SR); x[o:] += golpe(n - o, 70, 0.18, 1.2)
    m = int(0.5 * SR); x[o:o + m] += hp(rng.normal(0, 1, m), 0.9) * env(m, 0.05, 0.15) * 0.25
    return x

def candado():
    # candado del botiquín: clic con un muelle que vibra
    n = int(0.45 * SR); t = np.arange(n) / SR
    x = golpe(n, 2600, 0.02, 0.8)
    x += 0.3 * np.sin(2 * np.pi * 820 * t) * np.exp(-t / 0.12) * np.sin(2 * np.pi * 35 * t)
    o = int(0.12 * SR); x[o:] += golpe(n - o, 1900, 0.03, 0.5)
    return x

def tecla():
    n = int(0.12 * SR); t = np.arange(n) / SR
    return golpe(n, 3000, 0.004, 0.4) + 0.6 * np.sin(2 * np.pi * 1250 * t) * env(n, 0.002, 0.05) * (t < 0.08)

def clave_ok():
    n = int(0.7 * SR); x = np.zeros(n); t = np.arange(n) / SR
    for d, f in ((0.0, 1250), (0.12, 1660)):
        o = int(d * SR); m = int(0.09 * SR); x[o:o + m] += 0.6 * np.sin(2 * np.pi * f * t[:m]) * env(m, 0.002, 0.06)
    o = int(0.3 * SR); x[o:] += golpe(n - o, 140, 0.06, 0.8)   # relé del cerrojo
    return x

def clave_mal():
    n = int(0.45 * SR); t = np.arange(n) / SR
    return 0.5 * np.sign(np.sin(2 * np.pi * 220 * t)) * env(n, 0.003, 0.4) * (t < 0.38)

def recoger():
    # papel o tela que se dobla y se guarda: ráfagas de ruido filtrado
    n = int(0.5 * SR); x = np.zeros(n)
    for _ in range(14):
        p = int(rng.uniform(0, 0.38) * SR); m = int(rng.uniform(0.02, 0.07) * SR)
        x[p:p + m] += lp(hp(rng.normal(0, 1, m), 0.6), 0.3) * env(m, 0.003, 0.02) * rng.uniform(0.4, 1.0)
    return x

def llaves():
    # manojo de llaves: muchos tintineos agudos que se apagan
    n = int(0.6 * SR); x = np.zeros(n); t = np.arange(n) / SR
    for _ in range(18):
        p = int(rng.uniform(0, 0.35) * SR); m = n - p; f = rng.uniform(2800, 6200)
        x[p:] += rng.uniform(0.2, 0.6) * np.sin(2 * np.pi * f * t[:m]) * np.exp(-t[:m] / rng.uniform(0.02, 0.06))
    return x

def reja():
    # la reja del calabozo: golpe metálico grave y el traqueteo de los barrotes
    n = int(1.2 * SR); x = golpe(n, 180, 0.25, 1.0); t = np.arange(n) / SR
    x += 0.4 * sum(np.sin(2 * np.pi * f * t) for f in (530, 870, 1340)) * np.exp(-t / 0.35) * (0.6 + 0.4 * np.sin(2 * np.pi * 14 * t))
    return x

def barrera():
    # motor de la barrera del control de salida: zumbido que sube y un golpe al llegar arriba
    n = int(1.8 * SR); t = np.arange(n) / SR
    f = 90 + 40 * np.clip(t / 1.4, 0, 1)
    x = (np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3 + np.sin(2 * np.pi * np.cumsum(2 * f) / SR) * 0.3) * (t < 1.45) * env(n, 0.08, 10.0)
    x = lp(x, 0.6); o = int(1.45 * SR); x[o:] += golpe(n - o, 120, 0.1, 0.9)
    return x

def grillos(sec=12):
    # grillos de noche: varios a distinto ritmo, trinos de 4-5 kHz en ráfagas
    n = int((sec + 1) * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for f, rate, burst, ph, a in ((4300, 2.1, 0.32, 0.0, 1.0), (4650, 1.6, 0.25, 0.7, 0.6), (3950, 2.6, 0.2, 1.9, 0.45), (5100, 1.2, 0.4, 2.6, 0.3)):
        gate = (np.mod(t * rate + ph, 1.0) < burst) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 28 * t)))
        x += a * np.sin(2 * np.pi * f * t) * lp(gate.astype(float), 0.9)
    return bucle(x * (0.75 + 0.25 * np.sin(2 * np.pi * t / 7.3)))

def rumor(sec=16):
    # rumor lejano (camiones en la carretera, el mar, tormenta a lo lejos): ruido marrón muy grave que crece y se va
    n = int((sec + 1) * SR); t = np.arange(n) / SR
    b = np.cumsum(rng.normal(0, 1, n)); b -= lp(b, 0.9995)
    g = 0.6 + 0.4 * np.sin(2 * np.pi * t / 9.0) * np.sin(2 * np.pi * t / 4.1 + 0.5)
    return bucle(lp(lp(b, 0.97), 0.95) * g)

def empujon():
    # empujón: golpe sordo contra la ropa y el roce de las botas al trastabillar
    n = int(0.6 * SR); x = golpe(n, 85, 0.07, 1.0); t = np.arange(n) / SR
    o = int(0.08 * SR); m = int(0.35 * SR)
    x[o:o + m] += lp(rng.normal(0, 1, m), 0.7) * env(m, 0.01, 0.08) * 0.6
    o = int(0.3 * SR); x[o:] += golpe(n - o, 140, 0.03, 0.4)
    return x

def taquilla():
    # puerta de taquilla metálica: chirrido corto de bisagra y golpe de chapa
    n = int(0.7 * SR); t = np.arange(n) / SR
    f = 700 + 300 * np.sin(2 * np.pi * 1.6 * t)
    creak = lp(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)), 0.7) * (t < 0.35) * 0.25
    x = creak + 0.0
    o = int(0.38 * SR); x[o:] += golpe(n - o, 320, 0.08, 0.8)
    x[o:] += 0.3 * np.sin(2 * np.pi * 1450 * t[:n - o]) * np.exp(-t[:n - o] / 0.12)
    return x

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

# ---- música por capas (las tres duran lo mismo, MUS segundos, y empiezan juntas: siempre van a compás)
# Re menor oscuro a 75 ppm (0,8 s el pulso, 40 pulsos). Todas las frecuencias dan ciclos enteros en MUS: el bucle no corta.
MUS = 32.0

def ciclico(x, a):
    # paso bajo sin costura: se filtra la señal dos veces seguida y se queda la segunda vuelta
    return lp(np.concatenate([x, x]), a)[len(x):]

def tono(f, t):
    return np.sin(2 * np.pi * (round(f * MUS) / MUS) * t)   # frecuencia redondeada a ciclos enteros en el bucle

def musica_base():
    # ambiente: bordón grave de re con la quinta, que respira despacio, y un soplo de ruido como viento lejano
    n = int(MUS * SR); t = np.arange(n) / SR
    resp = 0.7 + 0.3 * np.sin(2 * np.pi * t / 16.0)          # dos respiraciones por vuelta
    x = (tono(73.42, t) + 0.6 * tono(110.0, t) + 0.35 * tono(146.83, t) + 0.15 * tono(174.61, t) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 8.0))) * resp
    x += ciclico(rng.normal(0, 1, n), 0.995) * 1.5
    return x

def musica_tension():
    # tensión: latido grave en cada pulso (dos golpes) y un trémolo agudo de segunda menor (la - si bemol) que inquieta
    n = int(MUS * SR); t = np.arange(n) / SR; x = np.zeros(n)
    beat = int(0.8 * SR)
    for k in range(40):
        for d, a in ((0.0, 1.0), (0.18, 0.6)):
            p = k * beat + int(d * SR); m = int(0.25 * SR)
            if p + m > n: continue
            tt = np.arange(m) / SR
            x[p:p + m] += a * np.sin(2 * np.pi * 55 * tt * (1 - 0.3 * tt)) * env(m, 0.004, 0.07)
    trem = 0.5 + 0.5 * np.sin(2 * np.pi * 6.25 * t)            # 6,25 Hz: 200 vueltas exactas
    x += 0.18 * (tono(440.0, t) + tono(466.16, t)) * trem * (0.6 + 0.4 * np.sin(2 * np.pi * t / 32.0))
    return x

def musica_alerta():
    # alerta: timbales al doble de pulso (0,4 s) y un ostinato de re - mi bemol en corcheas, áspero
    n = int(MUS * SR); x = np.zeros(n)
    step = int(0.4 * SR)
    for k in range(80):
        p = k * step; m = int(0.3 * SR)
        if p + m > n: continue
        tt = np.arange(m) / SR
        f = 82.4 if k % 4 in (0, 3) else 98.0
        x[p:p + m] += (1.0 if k % 2 == 0 else 0.7) * np.sin(2 * np.pi * f * tt * (1 - 0.4 * tt)) * env(m, 0.002, 0.09)
        x[p:p + m] += 0.25 * rng.normal(0, 1, m) * env(m, 0.001, 0.02)
    eighth = int(0.2 * SR)
    for k in range(160):
        p = k * eighth; m = int(0.17 * SR)
        if p + m > n: continue
        tt = np.arange(m) / SR
        f = 293.66 if k % 8 not in (3, 7) else 311.13
        sq = np.sign(np.sin(2 * np.pi * f * tt)) * 0.5 + np.sin(2 * np.pi * f * tt)
        x[p:p + m] += 0.12 * sq * env(m, 0.003, 0.08)
    return x

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
    save('musica_base', musica_base(), 0.5)
    save('musica_tension', musica_tension(), 0.5)
    save('musica_alerta', musica_alerta(), 0.55)
    # lo añadido después va al final: el generador de azar es el mismo y así los sonidos de antes no cambian
    for k in range(3):
        save('paso_metal_%d' % (k + 1), metal(k), 0.65)
        save('paso_madera_%d' % (k + 1), madera(k), 0.6)
        save('paso_hierba_%d' % (k + 1), hierba(k), 0.5)
    for nombre, f, pico in (('puerta_madera', puerta_madera, 0.7), ('puerta_blindada', puerta_blindada, 0.8), ('candado', candado, 0.6),
                            ('tecla', tecla, 0.5), ('clave_ok', clave_ok, 0.6), ('clave_mal', clave_mal, 0.5), ('recoger', recoger, 0.6),
                            ('llaves', llaves, 0.55), ('reja', reja, 0.8), ('barrera', barrera, 0.6), ('grillos', grillos, 0.35), ('rumor', rumor, 0.5)):
        save(nombre, f(), pico)
    save('empujon', empujon(), 0.7)
    save('taquilla', taquilla(), 0.6)