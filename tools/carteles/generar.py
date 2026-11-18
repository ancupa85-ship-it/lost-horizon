"""Carteles, rótulos y etiquetas de Tarsis (tanda 24): las texturas.

Se ejecuta con Python normal (Pillow y numpy), no en Unreal:  python tools/carteles/generar.py
Escribe un PNG por cartel en assets/unreal/carteles/ (van a git: son pequeños). Dónde va cada uno en el nivel lo dice
assets/unreal/carteles.json y lo coloca tools/unreal/carteles.py.

Tres clases:
- placa: chapa esmaltada atornillada (jefatura, archivo, cuerpo de guardia...). RGB = color; A = recorte (redonda o
  rectangular). Con su desgaste pintado: óxido que nace en los bordes y los tornillos, chorretones, desconchones, mugre.
- pintado: letras de plantilla pintadas en un muro o en la losa (calcomanía). RGB = color de la pintura; A = cuánta
  pintura queda (comida por el tiempo).
- etiqueta: cartulina mecanografiada en su marco (taquillas).
Todo sale de una semilla por cartel: se puede regenerar y da lo mismo. Los lados son potencias de dos (para que Unreal
les haga mipmaps); la proporción de verdad la pone el plano donde va.
Tipos de letra: Stardos Stencil (SIL OFL, en tools/carteles/fuentes) para lo pintado con plantilla; para las placas, una
palo seco negrita del sistema (Liberation Sans o Arial).
"""
import os, sys, math, zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, 'assets', 'unreal', 'carteles')
STENCIL = os.path.join(HERE, 'fuentes', 'StardosStencil-Bold.ttf')
SANS = next((f for f in ('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf',
                         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/Library/Fonts/Arial Bold.ttf') if os.path.exists(f)), None)
MAQUINA = next((f for f in ('/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf', 'C:/Windows/Fonts/courbd.ttf',
                            '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf') if os.path.exists(f)), None)
SS = 2      # se dibuja al doble y se reduce

BLANCO, NEGRO, ROJO, AMARILLO = (226, 222, 208), (26, 26, 28), (150, 28, 22), (214, 170, 22)
VERDE, AZUL = (58, 72, 44), (28, 52, 92)


def semilla(nombre):
    return zlib.crc32(nombre.encode('utf-8')) & 0x7fffffff


def ruido(w, h, rng, escala, octavas=4, caida=0.5):
    """Ruido de valor suavizado, 0-1: suma de rejillas aleatorias ampliadas."""
    acc = np.zeros((h, w), np.float32); amp, tot = 1.0, 0.0
    for o in range(octavas):
        gw, gh = max(2, int(w / escala * 2 ** o) + 2), max(2, int(h / escala * 2 ** o) + 2)
        g = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        acc += np.asarray(g, np.float32) / 255.0 * amp; tot += amp; amp *= caida
    return acc / tot


def paso(x, a, b):
    return np.clip((x - a) / (b - a), 0.0, 1.0)


def fuente(ruta, px):
    return ImageFont.truetype(ruta, max(6, int(px)))


def texto_centrado(d, caja, lineas, ruta, color, interlinea=1.12, ancho_max=0.9, espaciado=0):
    """lineas: [(texto, alto relativo)] dentro de caja (x0, y0, x1, y1). Ajusta el cuerpo para que quepan a lo ancho."""
    x0, y0, x1, y1 = caja
    W, H = x1 - x0, y1 - y0
    total = sum(a for _, a in lineas) * interlinea
    k = H / total
    y = y0 + (H - total * k) / 2 + (interlinea - 1) * k * 0.3
    for t, a in lineas:
        px = a * k * 0.82
        f = fuente(ruta, px)
        bb = d.textbbox((0, 0), t, font=f)
        while bb[2] - bb[0] > W * ancho_max and px > 8:
            px *= 0.96; f = fuente(ruta, px); bb = d.textbbox((0, 0), t, font=f)
        d.text((x0 + (W - (bb[2] - bb[0])) / 2 - bb[0], y + (a * k * interlinea - (bb[3] - bb[1])) / 2 - bb[1]), t, font=f, fill=color)
        y += a * k * interlinea


def desgaste(img, rng, tornillos, oxido=0.5, mugre=0.5, mascara=None):
    """Óxido desde los bordes y los tornillos, chorretones hacia abajo, desconchones y mugre. img: RGB float 0-1 (h, w, 3)."""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    borde = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / (0.09 * min(w, h))
    if mascara is not None:      # placa recortada: el borde es el del recorte
        m = Image.fromarray((mascara * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.05 * min(w, h)))
        borde = np.minimum(borde, np.clip((np.asarray(m, np.float32) / 255.0 - 0.5) * 6.0, 0, 9))
    cerca = np.clip(1.0 - borde, 0.0, 1.0)
    for tx, ty in tornillos:
        dd = np.hypot(xx - tx, yy - ty) / (0.07 * min(w, h))
        cerca = np.maximum(cerca, np.clip(1.25 - dd, 0.0, 1.0))
    n1 = ruido(w, h, rng, min(w, h) * 0.35, 5)
    n2 = ruido(w, h, rng, min(w, h) * 0.06, 3)
    ox = paso(cerca * 0.75 + n1 * 0.55 + n2 * 0.25, 1.02 - oxido * 0.42, 1.12 - oxido * 0.42)
    # chorretones: el óxido escurre hacia abajo y se va perdiendo
    ch = np.zeros_like(ox); fila = np.zeros(w, np.float32)
    hilos = paso(ruido(w, 1, rng, 9, 2)[0], 0.56, 0.62)             # solo de algunos puntos del borde
    for y in range(h):
        fila = np.maximum(fila * (1.0 - 3.2 / h), ox[y] * hilos)
        ch[y] = fila
    ch = np.asarray(Image.fromarray((ch * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255.0
    rojo = np.stack([0.33 + 0.16 * n2, 0.17 + 0.08 * n2, 0.07 + 0.03 * n2], -1)
    oscuro = np.stack([0.10 + 0.05 * n1, 0.065 + 0.03 * n1, 0.04 + 0.02 * n1], -1)
    c_ox = rojo * (1 - paso(n1, 0.45, 0.8))[..., None] + oscuro * paso(n1, 0.45, 0.8)[..., None]
    img = img * (1 - (ch * 0.45)[..., None]) + c_ox * (ch * 0.45)[..., None]
    img = img * (1 - ox[..., None]) + c_ox * ox[..., None]
    # desconchones: motas donde salta el esmalte y asoma la chapa oscura, con el canto claro
    d0 = ruido(w, h, rng, min(w, h) * 0.035, 2)
    zona = paso(ruido(w, h, rng, min(w, h) * 0.6, 2) + cerca * 0.35, 0.5, 0.75)        # a rodales, no por toda la placa
    desc = paso(d0 + cerca * 0.1, 0.775, 0.80) * zona * (1 - ox)
    img = img * (1 - desc[..., None]) + np.array([0.13, 0.12, 0.11], np.float32) * desc[..., None]
    # mugre: velo irregular, más abajo y en los bordes
    mg = (ruido(w, h, rng, min(w, h) * 0.5, 4) * 0.7 + (yy / h) * 0.3 + cerca * 0.25) * mugre
    img = img * (1.0 - 0.42 * np.clip(mg, 0, 1)[..., None])
    # arañazos finos
    ar = Image.new('L', (w, h), 0); da = ImageDraw.Draw(ar)
    for k in range(int(6 + 10 * mugre)):
        x, y = rng.integers(0, w), rng.integers(0, h); L = rng.integers(w // 20, w // 5); a = rng.uniform(-0.5, 0.5)
        da.line((x, y, x + L * math.cos(a), y + L * math.sin(a)), fill=int(rng.integers(40, 110)), width=1)
    ar = np.asarray(ar, np.float32) / 255.0
    return np.clip(img + ar[..., None] * 0.25 * (1 - ox[..., None]), 0, 1)


def tornillo(d, x, y, r):
    d.ellipse((x - r, y - r, x + r, y + r), fill=(62, 60, 56))
    d.ellipse((x - r * 0.72, y - r * 0.72, x + r * 0.72, y + r * 0.72), fill=(128, 124, 114))
    d.line((x - r * 0.5, y + r * 0.2, x + r * 0.5, y - r * 0.2), fill=(40, 38, 36), width=max(1, int(r * 0.28)))


def placa(nombre, w, h, fondo, lineas, color=NEGRO, filete=None, redonda=False, dibujo=None, oxido=0.5, mugre=0.5, banda=None):
    """lineas: [(texto, alto relativo[, color])]. filete: color del marco. banda: (color, fracción de alto arriba)."""
    rng = np.random.default_rng(semilla(nombre))
    W, H = w * SS, h * SS
    im = Image.new('RGB', (W, H), fondo); d = ImageDraw.Draw(im)
    m = int(min(W, H) * 0.055)
    msk = None
    if redonda:
        mk = Image.new('L', (W, H), 0); ImageDraw.Draw(mk).ellipse((2, 2, W - 3, H - 3), fill=255)
    if banda:
        d.rectangle((0, 0, W, int(H * banda[1])), fill=banda[0])
    if filete and not redonda:
        d.rounded_rectangle((m, m, W - m, H - m), radius=m, outline=filete, width=max(2, int(min(W, H) * 0.022)))
    caja = (m * 2.2, m * 1.8, W - m * 2.2, H - m * 1.8)
    if dibujo:
        caja = dibujo(d, W, H, caja) or caja
    if lineas:
        # cada línea con su color: se dibujan por separado sobre la misma caja repartida
        x0, y0, x1, y1 = caja
        tot = sum(l[1] for l in lineas); y = y0
        for l in lineas:
            hh = (y1 - y0) * l[1] / tot
            texto_centrado(d, (x0, y, x1, y + hh), [(l[0], 1.0)], SANS, l[2] if len(l) > 2 else color, interlinea=1.0)
            y += hh
    r = min(W, H) * 0.026
    ts = [] if redonda else [(m * 1.15, m * 1.15), (W - m * 1.15, m * 1.15), (m * 1.15, H - m * 1.15), (W - m * 1.15, H - m * 1.15)]
    if redonda:
        ts = [(W / 2, m * 0.9), (W / 2, H - m * 0.9)]
    for tx, ty in ts:
        tornillo(d, tx, ty, r)
    im = im.resize((w, h), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0
    # el esmalte nunca es liso: aguas suaves y un punto de amarilleo
    a *= (0.93 + 0.1 * ruido(w, h, rng, min(w, h) * 0.8, 3))[..., None]
    alfa = np.ones((h, w), np.float32)
    if redonda:
        alfa = np.asarray(mk.resize((w, h), Image.LANCZOS), np.float32) / 255.0
    a = desgaste(a, rng, [(x / SS, y / SS) for x, y in ts], oxido, mugre, alfa if redonda else None)
    out = np.dstack([a, alfa])
    guardar(nombre, out)


def pintado(nombre, w, h, lineas, color=(222, 218, 205), ruta=None, gasto=0.45, dibujo=None):
    """Letras de plantilla pintadas: RGB el color de la pintura (liso, con un poco de variación) y A lo que queda de ella."""
    rng = np.random.default_rng(semilla(nombre))
    W, H = w * SS, h * SS
    mk = Image.new('L', (W, H), 0); d = ImageDraw.Draw(mk)
    caja = (W * 0.03, H * 0.06, W * 0.97, H * 0.94)
    if dibujo:
        caja = dibujo(d, W, H, caja) or caja
    if lineas:
        texto_centrado(d, caja, lineas, ruta or STENCIL, 255, interlinea=1.08, ancho_max=0.98)
    mk = mk.filter(ImageFilter.GaussianBlur(SS * 0.6)).resize((w, h), Image.LANCZOS)      # borde de brocha, no de imprenta
    m = np.asarray(mk, np.float32) / 255.0
    n1 = ruido(w, h, rng, min(w, h) * 0.5, 5); n2 = ruido(w, h, rng, min(w, h) * 0.04, 3)
    queda = 1.0 - paso(n1 * 0.6 + n2 * 0.4, 0.62 - gasto * 0.3, 0.78 - gasto * 0.3) * 0.85     # calvas
    queda *= 0.72 + 0.28 * ruido(w, h, rng, 3.0, 2)                                            # grano del soporte
    alfa = m * np.clip(queda, 0, 1)
    c = np.array(color, np.float32) / 255.0
    rgb = np.ones((h, w, 3), np.float32) * c * (0.9 + 0.1 * n1)[..., None]
    guardar(nombre, np.dstack([np.clip(rgb, 0, 1), alfa]))


def etiqueta(nombre, w, h, lineas):
    """Cartulina mecanografiada en un marco de chapa (taquillas)."""
    rng = np.random.default_rng(semilla(nombre))
    W, H = w * SS, h * SS
    im = Image.new('RGB', (W, H), (70, 74, 60)); d = ImageDraw.Draw(im)
    m = int(H * 0.13)
    d.rectangle((m, m, W - m, H - m), fill=(206, 196, 168))
    texto_centrado(d, (m * 1.6, m * 1.3, W - m * 1.6, H - m * 1.3), lineas, MAQUINA or SANS, (38, 34, 40), interlinea=1.05)
    im = im.resize((w, h), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0
    a *= (0.8 + 0.2 * ruido(w, h, rng, h * 0.7, 3))[..., None]
    a = np.clip(a - paso(ruido(w, h, rng, h * 0.3, 3), 0.62, 0.75)[..., None] * 0.07, 0, 1)   # manchas de dedos y humedad
    guardar(nombre, np.dstack([a, np.ones((h, w), np.float32)]))


def guardar(nombre, rgba):
    os.makedirs(OUT, exist_ok=True)
    im = Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')
    im.save(os.path.join(OUT, nombre + '.png'), optimize=True)
    print('  +', nombre, im.size)


# ---------------------------------------------------------------- dibujos

def d_triangulo_rayo(d, W, H, caja):
    """Triángulo de peligro con el rayo, arriba; el texto queda debajo."""
    cx, top, lado = W / 2, H * 0.07, min(W * 0.62, H * 0.5)
    alto = lado * 0.866
    p = [(cx, top), (cx + lado / 2, top + alto), (cx - lado / 2, top + alto)]
    d.polygon(p, fill=NEGRO)
    k = 0.8; c = (cx, top + alto * 0.62)
    q = [(c[0] + (x - c[0]) * k, c[1] + (y - c[1]) * k) for x, y in p]
    d.polygon(q, fill=AMARILLO)
    s = alto * 0.085
    rayo = [(1.2, -3.0), (-1.6, 0.4), (-0.1, 0.4), (-1.3, 3.6), (1.7, -0.5), (0.2, -0.5)]
    d.polygon([(c[0] + x * s, c[1] + y * s) for x, y in rayo], fill=NEGRO)
    return (caja[0], top + alto + H * 0.03, caja[2], caja[3])


def d_velocidad(d, W, H, caja):
    d.ellipse((2, 2, W - 3, H - 3), fill=ROJO)
    g = W * 0.15
    d.ellipse((g, g, W - g, H - g), fill=BLANCO)
    return (W * 0.2, H * 0.24, W * 0.8, H * 0.76)


def d_alto(d, W, H, caja):
    """Disco rojo con ALTO, arriba; debajo, el texto en negro."""
    r = min(W * 0.36, H * 0.26); cx, cy = W / 2, H * 0.06 + r
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ROJO)
    d.ellipse((cx - r * 0.9, cy - r * 0.9, cx + r * 0.9, cy + r * 0.9), outline=BLANCO, width=max(2, int(r * 0.05)))
    texto_centrado(d, (cx - r * 0.82, cy - r * 0.4, cx + r * 0.82, cy + r * 0.4), [('ALTO', 1.0)], SANS, BLANCO, interlinea=1.0, ancho_max=1.0)
    return (caja[0], cy + r + H * 0.03, caja[2], caja[3])


def d_cruz(d, W, H, caja):
    s = min(W, H) * 0.3; cx, cy = W * 0.2, H / 2
    d.rectangle((cx - s / 2, cy - s / 6, cx + s / 2, cy + s / 6), fill=ROJO)
    d.rectangle((cx - s / 6, cy - s / 2, cx + s / 6, cy + s / 2), fill=ROJO)
    return (W * 0.36, caja[1], caja[2], caja[3])


def d_linea(d, W, H, caja):
    d.rectangle((0, H * 0.08, W, H * 0.92), fill=255)
    return (0, 0, 1, 1)


# ---------------------------------------------------------------- la lista

def todo():
    if not SANS:
        sys.exit('falta una palo seco negrita (Liberation Sans o Arial)')
    # placas de puerta: esmalte blanco, letra negra, filete negro
    placa('jefatura', 1024, 256, BLANCO, [('JEFATURA', 1.0)], filete=NEGRO, oxido=0.35, mugre=0.35)
    placa('archivo', 1024, 512, BLANCO, [('ARCHIVO', 1.25), ('ACCESO RESTRINGIDO', 0.6, ROJO)], filete=NEGRO, oxido=0.4, mugre=0.4)
    placa('dormitorio', 1024, 256, BLANCO, [('DORMITORIO DE TROPA', 1.0)], filete=NEGRO, oxido=0.6, mugre=0.6)
    placa('cuerpo_guardia', 1024, 256, BLANCO, [('CUERPO DE GUARDIA', 1.0)], filete=NEGRO, oxido=0.6, mugre=0.55)
    placa('calabozo', 1024, 256, BLANCO, [('CALABOZO', 1.0)], filete=NEGRO, oxido=0.45, mugre=0.5)
    placa('zona_restringida', 1024, 512, ROJO, [('ZONA RESTRINGIDA', 1.2), ('SOLO PERSONAL AUTORIZADO', 0.62)], color=BLANCO, filete=BLANCO, oxido=0.6, mugre=0.55)
    # perímetro
    # tanda 25: de noche no se leía. La chapa pasa a 2 x 1 m (carteles.json), el rótulo grande ocupa casi todo el ancho
    # y lleva menos óxido y menos mugre encima (lo que se come el contraste de noche es el velo, no el tamaño solo)
    placa('zona_militar', 1024, 512, AMARILLO, [('ZONA MILITAR', 1.5), ('PROHIBIDO ACERCARSE AL MURO', 0.5)], filete=NEGRO, oxido=0.45, mugre=0.3)
    placa('portillo', 1024, 512, BLANCO, [('PORTILLO N.º 2', 1.1), ('MANTENER CERRADO', 0.7, ROJO)], filete=NEGRO, oxido=0.75, mugre=0.7)
    # control de salida y camino
    placa('alto_control', 512, 1024, BLANCO, [('CONTROL', 1.0), ('DE SALIDA', 1.0), ('PRESENTE SU', 0.62), ('DOCUMENTACIÓN', 0.62)], filete=NEGRO, dibujo=d_alto, oxido=0.5, mugre=0.5)
    placa('velocidad_20', 512, 512, BLANCO, [('20', 1.0)], redonda=True, dibujo=d_velocidad, oxido=0.55, mugre=0.5)
    # peligros
    placa('alta_tension', 512, 1024, AMARILLO, [('PELIGRO', 1.0), ('ALTA TENSIÓN', 0.75), ('GRUPO ELECTRÓGENO', 0.5)], filete=NEGRO, dibujo=d_triangulo_rayo, oxido=0.55, mugre=0.5)
    placa('gasoleo', 1024, 512, BLANCO, [('PROHIBIDO FUMAR', 1.1, ROJO), ('GASÓLEO · INFLAMABLE', 0.7)], filete=ROJO, oxido=0.65, mugre=0.6)
    placa('botiquin', 1024, 512, BLANCO, [('BOTIQUÍN', 1.0)], filete=NEGRO, dibujo=d_cruz, oxido=0.3, mugre=0.35)
    # pintado con plantilla
    pintado('lema', 2048, 256, [('TODO POR LA PATRIA', 1.0)], gasto=0.3)      # tanda 25: menos comido (0,5): se leía a trozos
    pintado('alto_suelo', 1024, 512, [('ALTO', 1.0)], gasto=0.6)
    pintado('linea_alto', 512, 64, [], gasto=0.55, dibujo=d_linea)
    pintado('numero_2', 256, 256, [('2', 1.0)], gasto=0.45)
    # etiquetas de las taquillas
    for i, t in enumerate((('CABO 1.º LOBATO', 'TAQUILLA 14'), ('SDO. RAMOS', 'TAQUILLA 15'), ('RETÉN', 'TAQUILLA 3'))):
        etiqueta('etiqueta_%d' % (i + 1), 256, 128, [(t[0], 1.0), (t[1], 0.8)])


if __name__ == '__main__':
    todo()
