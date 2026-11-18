"""Música de Tarsis por capas (tanda 29) y los sonidos del códec, como .wav en assets/unreal/sonidos.

Tres capas que duran lo mismo y suenan a la vez (ATarsisDirector::SetupMusic): «musica_base» siempre, «musica_tension»
con la sospecha y «musica_alerta» con la alarma. Están escritas juntas, sobre la misma armonía, para que al entrar
una encima de otra sigan siendo una sola pieza: 16 compases de 4/4 a 75 ppm (51,2 s) en re menor.

  base     colchón de cuerdas graves, bajo, un piano lejano con el tema («De profundis»: sube desde el re) y su eco
  tensión  latido, ostinato de cuerda grave en corcheas sobre la fundamental, trémolo agudo la-si bemol y un tic de reloj
  alerta   bombo, caja y timbales, bajo en semicorcheas y golpes de metal con el acorde

Todo sintetizado con numpy (suma de armónicos, filtros y reverberación por FFT, que al ser cíclica deja el bucle sin
costura): sin bancos de sonidos ni licencias. Estéreo a 32 kHz.
Uso: python3 tools/sonido/generar_musica.py
"""
import os, wave
import numpy as np

SR = 32000
BEAT = 0.8
BAR = 4 * BEAT
BARS = 16
N = int(round(BARS * BAR * SR))
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets', 'unreal', 'sonidos')
rng = np.random.default_rng(29)

A4 = 440.0
NOTAS = {'C': -9, 'C#': -8, 'D': -7, 'Eb': -6, 'E': -5, 'F': -4, 'F#': -3, 'G': -2, 'G#': -1, 'A': 0, 'Bb': 1, 'B': 2}

def hz(nombre):
    """'D3', 'Bb1', 'C#4' -> Hz"""
    n, o = nombre[:-1], int(nombre[-1])
    return A4 * 2 ** ((NOTAS[n] + 12 * (o - 4)) / 12.0)

def s(beats):
    return int(round(beats * BEAT * SR))

def nuevo():
    return np.zeros((2, N))

def poner(buf, inicio, x, pan=0.0, vol=1.0):
    """Suma x (mono) en el bucle desde la muestra «inicio», dando la vuelta al final: las colas no se cortan."""
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    idx = (inicio + np.arange(len(x))) % N
    np.add.at(buf[0], idx, x * vol * l)
    np.add.at(buf[1], idx, x * vol * r)

def armonicos(f, n, amp, fase=None):
    """Suma de armónicos limitada en banda: amp(k) es el peso del armónico k."""
    t = np.arange(n) / SR
    x = np.zeros(n)
    k = 1
    while k * f < SR * 0.45 and k <= 48:
        a = amp(k)
        if a > 1e-4:
            x += a * np.sin(2 * np.pi * k * f * t + (0.0 if fase is None else fase * k))
        k += 1
    return x

def sierra(f, n, brillo=1.0, fase=0.0):
    return armonicos(f, n, lambda k: (1.0 / k) * np.exp(-k * f / (2500.0 * brillo)), fase)

def envolvente(n, ataque, caida, sosten=1.0, suelta=0.05):
    """Ataque lineal, caída exponencial hasta «sosten» y suelta al final (segundos)."""
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(ataque, 1e-4)) * (sosten + (1 - sosten) * np.exp(-t / max(caida, 1e-4)))
    r = int(suelta * SR)
    if 0 < r < n:
        e[-r:] *= np.linspace(1, 0, r)
    return e

def coseno(n, entra, sale):
    """Entra y sale con medio coseno (segundos): para notas largas de colchón."""
    e = np.ones(n)
    a, b = int(entra * SR), int(sale * SR)
    e[:a] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    e[-b:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, b))
    return e

def filtro(buf, corte, orden=2, alto=False):
    """Paso bajo (o alto) por FFT sobre el bucle entero: cíclico, sin costura."""
    f = np.fft.rfftfreq(buf.shape[-1], 1.0 / SR)
    g = 1.0 / np.sqrt(1.0 + (f / corte) ** (2 * orden))
    if alto:
        g = np.sqrt(np.maximum(0.0, 1.0 - g * g))
    return np.fft.irfft(np.fft.rfft(buf, axis=-1) * g, n=buf.shape[-1], axis=-1)

def reverb(buf, segundos=3.2, mezcla=0.35, corte=3500.0):
    """Reverberación de sala grande: convolución cíclica con ruido que decae, distinto en cada oído."""
    m = int(segundos * 2.2 * SR)
    t = np.arange(m) / SR
    out = np.empty_like(buf)
    for c in range(2):
        ir = np.zeros(N)
        ir[:m] = rng.normal(0, 1, m) * np.exp(-t * 6.9 / segundos) * np.minimum(1.0, t / 0.012)
        ir = filtro(ir[None, :], corte)[0]
        ir /= np.sqrt(np.sum(ir ** 2))
        out[c] = np.fft.irfft(np.fft.rfft(buf[c]) * np.fft.rfft(ir), n=N)
    return buf * (1 - mezcla) + out * mezcla

def guardar(nombre, buf, pico):
    buf = buf / (np.max(np.abs(buf)) + 1e-9) * pico
    os.makedirs(OUT, exist_ok=True)
    datos = (buf.T * 32767).astype('<i2') if buf.ndim == 2 else (buf * 32767).astype('<i2')
    with wave.open(os.path.join(OUT, nombre + '.wav'), 'wb') as w:
        w.setnchannels(2 if buf.ndim == 2 else 1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(datos.tobytes())
    print(nombre, round(buf.shape[-1] / SR, 2), 's', 'estéreo' if buf.ndim == 2 else 'mono')

# ---------------------------------------------------------------- la armonía: un acorde cada dos compases
# (bajo, notas del colchón). El 7.º y el 15.º resuelven a la dominante en su segundo compás.
ACORDES = [
    ('D2',  ['D3', 'F3', 'A3', 'E4']),          # re menor con novena
    ('Bb1', ['D3', 'F3', 'A3', 'Bb3']),         # si bemol con séptima mayor
    ('G1',  ['D3', 'G3', 'Bb3', 'A3']),         # sol menor con novena
    ('A1',  ['D3', 'E3', 'A3'], ['C#3', 'E3', 'A3']),   # la suspendida -> la mayor
    ('D2',  ['D3', 'F3', 'A3', 'E4']),
    ('C2',  ['C3', 'F3', 'A3', 'E4']),          # fa sobre do
    ('Bb1', ['D3', 'E3', 'G3', 'Bb3']),         # sol menor con sexta, sobre si bemol
    ('A1',  ['E3', 'G3', 'Bb3'], ['E3', 'A3', 'C#4']),  # la con novena menor -> la mayor
]

def raiz(compas):
    return ACORDES[(compas // 2) % 8][0]

# ---------------------------------------------------------------- instrumentos

def cuerda(f, n, brillo=0.6, desafina=7.0):
    """Sección de cuerda: tres sierras algo desafinadas, cada una a un lado. Devuelve (centro, izquierda, derecha)."""
    c = 2 ** (desafina / 1200.0)
    return (sierra(f, n, brillo, rng.uniform(0, 6)), sierra(f / c, n, brillo, rng.uniform(0, 6)), sierra(f * c, n, brillo, rng.uniform(0, 6)))

def piano(f, dur, fuerza=1.0):
    """Piano con sordina, lejano: parciales algo inarmónicos que decaen antes cuanto más agudos."""
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.0005 * k * k)
        if fk > SR * 0.45: break
        x += (fuerza ** (k - 1)) / k ** 1.5 * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6)) * np.exp(-t * (0.55 + 0.35 * k) * (f / 300.0) ** 0.4)
    golpe = rng.normal(0, 1, n) * np.exp(-t / 0.004) * 0.08          # el macillo
    return (x + golpe) * np.minimum(1.0, t / 0.004) * envolvente(n, 0.001, 9.0, 1.0, 0.08)

def golpe_grave(f0, f1, dur, caida):
    """Parche grave (latido, bombo, timbal): seno que cae de f0 a f1."""
    n = int(dur * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / caida) * np.minimum(1.0, t / 0.002)

def ruido(dur, caida, ataque=0.001):
    n = int(dur * SR); t = np.arange(n) / SR
    return rng.normal(0, 1, n) * np.exp(-t / caida) * np.minimum(1.0, t / ataque)

# ---------------------------------------------------------------- las tres capas

def capa_base():
    cuerdas, bajo, teclas = nuevo(), nuevo(), nuevo()
    solape = 1.0
    for i, ac in enumerate(ACORDES):
        partes = [(ac[1], 0.0, 2 * BAR)] if len(ac) == 2 else [(ac[1], 0.0, BAR), (ac[2], BAR, BAR)]
        for notas, desde, largo in partes:
            n = int((largo + solape) * SR)
            e = coseno(n, solape, solape)
            respira = 0.8 + 0.2 * np.sin(2 * np.pi * np.arange(n) / SR / (2 * BAR) + i)
            for j, nota in enumerate(notas):
                c, l, r = cuerda(hz(nota), n, 0.8)
                ini = int((i * 2 * BAR + desde - solape / 2) * SR)
                v = 0.5 if j else 0.6
                poner(cuerdas, ini, c * e * respira, 0.0, v)
                poner(cuerdas, ini, l * e * respira, -0.8, v * 0.8)
                poner(cuerdas, ini, r * e * respira, 0.8, v * 0.8)
        # bajo: la fundamental, con su octava muy atrás
        n = int((2 * BAR + solape) * SR)
        f = hz(ac[0])
        t = np.arange(n) / SR
        poner(bajo, int((i * 2 * BAR - solape / 2) * SR), (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * 2 * f * t) + 0.3 * np.sin(2 * np.pi * 3 * f * t)) * coseno(n, solape, solape), 0.0, 1.0)
    cuerdas = filtro(cuerdas, 1100.0, 2)
    cuerdas = reverb(cuerdas, 3.0, 0.45, 2500.0)

    # el tema, en la segunda mitad (compases 9 a 16): (compás, tiempo, nota, tiempos que dura)
    tema = [(8, 0, 'D4', 1), (8, 1, 'F4', 1), (8, 2, 'E4', 2),
            (9, 0, 'D4', 1), (9, 1, 'A4', 3),
            (10, 0, 'G4', 1), (10, 1, 'F4', 1), (10, 2, 'E4', 2),
            (11, 0, 'C4', 1), (11, 1, 'F4', 3),
            (12, 0, 'Bb4', 1.5), (12, 1.5, 'A4', 0.5), (12, 2, 'G4', 2),
            (13, 0, 'E4', 1), (13, 1, 'G4', 3),
            (14, 0, 'A4', 1), (14, 1, 'Bb4', 1), (14, 2, 'A4', 2),
            (15, 0, 'E4', 2), (15, 2, 'C#4', 2)]
    for compas, tiempo, nota, dur in tema:
        poner(teclas, s(compas * 4 + tiempo), piano(hz(nota), dur * BEAT + 2.5, 0.8), rng.uniform(-0.25, 0.25), 0.9)
        poner(teclas, s(compas * 4 + tiempo), piano(hz(nota) / 2, dur * BEAT + 2.5, 0.6), 0.0, 0.25)   # la octava de abajo, de sombra
    # la primera mitad, casi vacía: notas sueltas que anuncian el tema
    for compas, tiempo, nota in [(1, 2, 'A4'), (3, 1, 'D5'), (5, 2, 'Bb4'), (5, 3, 'A4'), (7, 2, 'E4')]:
        poner(teclas, s(compas * 4 + tiempo), piano(hz(nota), 4.0, 0.7), rng.uniform(-0.5, 0.5), 0.55)
    teclas = filtro(teclas, 2600.0, 1)
    teclas = reverb(teclas, 4.0, 0.6, 3000.0)

    aire = filtro(filtro(rng.normal(0, 1, (2, N)), 900.0, 1), 250.0, 1, alto=True)
    aire *= 0.6 + 0.4 * np.sin(2 * np.pi * np.arange(N) / N * 4 + np.array([[0.0], [1.3]]))
    norm = lambda b: b / (np.max(np.abs(b)) + 1e-9)
    return norm(cuerdas) * 0.8 + norm(filtro(bajo, 300.0, 2)) * 0.2 + norm(teclas) * 0.8 + norm(aire) * 0.05

def capa_tension():
    cuerdas, latido, alto, tic = nuevo(), nuevo(), nuevo(), nuevo()
    for compas in range(BARS):
        f = hz(raiz(compas)) * 2          # una octava sobre el bajo
        vecina = f * 2 ** (1 / 12.0)      # la segunda menor de arriba: la que inquieta
        crece = 0.55 + 0.45 * ((compas % 4) + 1) / 4.0
        for c in range(8):                # corcheas: fundamental, con la vecina en la 4.ª y la 7.ª
            nota = vecina if c in (3, 6) else f
            n = int(0.36 * SR)
            x = sierra(nota, n, 0.9, rng.uniform(0, 6)) * envolvente(n, 0.02, 0.12, 0.25, 0.06)
            poner(cuerdas, s(compas * 4 + c * 0.5), x, -0.3 if c % 2 else 0.3, crece * (1.0 if c % 4 == 0 else 0.7))
        for t0, a in ((0.0, 1.0), (0.23, 0.6), (2.0, 0.85), (2.23, 0.5)):   # latido: dos golpes, dos veces por compás
            poner(latido, s(compas * 4 + t0), golpe_grave(75.0, 42.0, 0.5, 0.11), 0.0, a)
        for d in range(16):               # tic de reloj en semicorcheas, apenas
            if d % 4 == 0: continue
            poner(tic, s(compas * 4 + d * 0.25), ruido(0.03, 0.004), 0.6 if d % 2 else -0.6, 0.5 if d % 2 else 0.9)
    # trémolo agudo la - si bemol, que entra y se va cada cuatro compases
    n = N; t = np.arange(n) / SR
    trem = 0.55 + 0.45 * np.sin(2 * np.pi * 7.5 * t)
    ola = 0.5 - 0.5 * np.cos(2 * np.pi * t / (4 * BAR))
    for nota, pan in (('A5', -0.5), ('Bb5', 0.5), ('A4', 0.0)):
        f = round(hz(nota) * N / SR) * SR / N          # ciclos enteros en el bucle
        poner(alto, 0, (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * trem * ola, pan, 0.5)
    cuerdas = reverb(filtro(cuerdas, 1100.0, 2), 1.8, 0.3)
    alto = reverb(alto, 3.0, 0.5)
    tic = filtro(tic, 5000.0, 2, alto=True)
    norm = lambda b: b / (np.max(np.abs(b)) + 1e-9)
    return norm(cuerdas) * 0.8 + norm(filtro(latido, 200.0, 2)) * 0.6 + norm(alto) * 0.2 + norm(tic) * 0.1

def capa_alerta():
    parches, caja, bajo, metal, platos = nuevo(), nuevo(), nuevo(), nuevo(), nuevo()
    for compas in range(BARS):
        b0 = compas * 4
        for t0, a in ((0, 1.0), (1.5, 0.8), (2, 0.95), (3.5, 0.7)):                # bombo
            poner(parches, s(b0 + t0), golpe_grave(120.0, 45.0, 0.45, 0.09), 0.0, a)
        for t0 in (1, 3):                                                         # caja
            x = ruido(0.22, 0.05) * 0.8 + golpe_grave(240.0, 170.0, 0.22, 0.04)
            poner(caja, s(b0 + t0), x, 0.1, 1.0)
        if compas % 2 == 1:                                                       # redoble de timbales al final de cada dos compases
            for k, (t0, fz) in enumerate(((3.0, 110.0), (3.25, 110.0), (3.5, 90.0), (3.75, 75.0))):
                poner(parches, s(b0 + t0), golpe_grave(fz * 1.6, fz, 0.5, 0.14), -0.6 + 0.4 * k, 0.75)
        for d in range(16):                                                       # platos cerrados en semicorcheas
            poner(platos, s(b0 + d * 0.25), ruido(0.05, 0.012 if d % 4 else 0.03), 0.4, 1.0 if d % 4 == 2 else 0.55)
        f = hz(raiz(compas)) * 2                                                   # bajo en semicorcheas: fundamental y octava
        for d in range(16):
            nota = f * (2.0 if d % 8 in (3, 6) else 1.0) * (2 ** (1 / 12.0) if d == 15 and compas % 2 == 1 else 1.0)
            n = int(0.19 * SR)
            x = sierra(nota, n, 1.6, rng.uniform(0, 6)) * envolvente(n, 0.004, 0.06, 0.15, 0.03)
            poner(bajo, s(b0 + d * 0.25), x, 0.0, 1.0 if d % 4 == 0 else 0.7)
        # metales: el acorde, golpe al principio del compás y otro a contratiempo
        ac = ACORDES[(compas // 2) % 8]
        notas = ac[2] if len(ac) == 3 and compas % 2 == 1 else ac[1]
        for t0, dur, a in ((0, 1.4, 1.0), (2.5, 0.5, 0.75)):
            n = int(dur * BEAT * SR)
            for j, nota in enumerate(notas):
                x = sierra(hz(nota), n, 2.2, rng.uniform(0, 6)) * envolvente(n, 0.03, 0.35, 0.55, 0.08)
                poner(metal, s(b0 + t0), x, -0.5 + j * 0.33, a)
    bajo = filtro(bajo, 900.0, 2)
    metal = reverb(filtro(metal, 1800.0, 2), 1.6, 0.3)
    platos = filtro(platos, 6000.0, 2, alto=True)
    parches = reverb(parches, 1.2, 0.15)
    caja = reverb(filtro(caja, 5000.0, 1), 1.2, 0.2)
    norm = lambda b: b / (np.max(np.abs(b)) + 1e-9)
    return norm(parches) * 1.0 + norm(caja) * 0.55 + norm(bajo) * 0.6 + norm(metal) * 0.55 + norm(platos) * 0.12

# ---------------------------------------------------------------- sonidos del códec (mono)

def codec_llamada():
    # dos timbrazos: un trino entre dos tonos, cortado por el altavoz pequeño
    n = int(1.3 * SR); t = np.arange(n) / SR
    trino = np.where(np.sin(2 * np.pi * 22 * t) > 0, 1480.0, 1760.0)
    x = np.sin(2 * np.pi * np.cumsum(trino) / SR)
    puerta = ((t % 0.65) < 0.42).astype(float)
    borde = np.minimum(1.0, np.minimum(t % 0.65, np.abs(0.42 - (t % 0.65))) / 0.01)
    return np.tanh(x * 1.5) * puerta * borde

def codec_abrir():
    n = int(0.28 * SR); t = np.arange(n) / SR
    barrido = np.sin(2 * np.pi * (500 * t + 4500 * t * t))
    return barrido * np.exp(-t / 0.12) + rng.normal(0, 1, n) * np.exp(-t / 0.03) * 0.3

def codec_cerrar():
    n = int(0.22 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (1800 * t - 3000 * t * t)) * np.exp(-t / 0.08) + rng.normal(0, 1, n) * np.exp(-t / 0.015) * 0.25

def codec_tecla(f=900.0, dur=0.022):
    n = int(dur * SR); t = np.arange(n) / SR
    return np.sign(np.sin(2 * np.pi * f * t)) * np.minimum(1.0, t / 0.001) * np.minimum(1.0, (dur - t) / 0.004)

if __name__ == '__main__':
    guardar('musica_base', capa_base(), 0.7)
    guardar('musica_tension', capa_tension(), 0.7)
    guardar('musica_alerta', capa_alerta(), 0.8)
    guardar('codec_llamada', codec_llamada(), 0.5)
    guardar('codec_abrir', codec_abrir(), 0.5)
    guardar('codec_cerrar', codec_cerrar(), 0.45)
    guardar('codec_tecla', codec_tecla(), 0.3)
    guardar('codec_tecla_grave', codec_tecla(220.0, 0.035), 0.35)
