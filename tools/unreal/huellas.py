"""Tanda D: lo que necesitan las huellas (TarsisHuellas.cpp). Se ejecuta en el editor:  py tools/unreal/huellas.py

1. T_Huella: la suela de una bota militar en escala de grises (256 x 256, la suela de arriba abajo; blanco donde pisa),
   con el taco del tacon, los tacos de la planta y un poco de ruido para que no sea un sello. Se dibuja aqui (sin
   descargas) y se guarda en D:\\LostHorizon\\descargas\\huella.png antes de importarla.
2. M_Huella: calcomania modulada (con Substrate es la que oscurece solo dentro de la mascara: ver docs/rendimiento.md,
   tanda 23; la mezcla se pone ANTES que el dominio de calcomania). Parametros:
   - Fuerza: la opacidad (el C++ la baja al borrarse la huella, y agachado).
   - Mojada: 0 barro (pardo oscuro), 1 agua sobre suelo duro (casi negro, mas tenue).
   - Girar: 0/1 cambia U y V (por si la suela sale atravesada respecto al paso: se arregla aqui sin compilar).
Escribe D:\\LostHorizon\\huellas_info.txt."""
import math
import os
import random

import unreal

DM = '/Game/Tarsis/Materiales'
TEX = '/Game/Tarsis/Texturas'
PNG = r'D:\LostHorizon\descargas\huella.png'
L = []
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def w(s):
    L.append(str(s))


def png_gris(ruta, ancho, alto, px):
    """PNG de 8 bits en gris sin dependencias (zlib + struct)."""
    import struct, zlib
    filas = b''.join(b'\x00' + bytes(px[y * ancho:(y + 1) * ancho]) for y in range(alto))
    def trozo(tipo, datos):
        c = struct.pack('>I', len(datos)) + tipo + datos
        return c + struct.pack('>I', zlib.crc32(tipo + datos) & 0xffffffff)
    with open(ruta, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(trozo(b'IHDR', struct.pack('>IIBBBBB', ancho, alto, 8, 0, 0, 0, 0)))
        f.write(trozo(b'IDAT', zlib.compress(filas, 9)))
        f.write(trozo(b'IEND', b''))


def textura():
    N = 256
    rs = random.Random(1983)
    px = [0] * (N * N)
    for y in range(N):
        for x in range(N):
            u = (x + 0.5) / N - 0.5          # -0,5 .. 0,5 a lo ancho
            v = (y + 0.5) / N                # 0 punta .. 1 talon
            # contorno: la planta (ancha, de 0,04 a 0,62) y el tacon (de 0,70 a 0,97), con el puente estrecho entre medias
            if v < 0.04 or v > 0.97:
                continue
            if v < 0.62:
                t = (v - 0.04) / 0.58
                half = 0.20 + 0.11 * math.sin(math.pi * min(1.0, t * 1.3))
                cx = 0.02 * math.sin(math.pi * t)
            elif v < 0.70:
                half, cx = 0.15, 0.02
            else:
                half, cx = 0.21, 0.0
            dx = (u - cx) / half
            if abs(dx) > 1.0:
                continue
            # bordes redondeados en la punta y el talon
            if v < 0.12 and dx * dx + ((0.12 - v) / 0.08) ** 2 > 1.0:
                continue
            if v > 0.90 and dx * dx + ((v - 0.90) / 0.07) ** 2 > 1.0:
                continue
            on = 1.0
            # tacos: barras cruzadas en la planta, rejilla en el tacon; el puente casi no pisa
            if v < 0.62:
                on = 1.0 if (int(v * 26) % 2 == 0) else 0.35
                if abs(dx) > 0.82:
                    on = 1.0                          # el borde de la suela pisa entero
            elif v < 0.70:
                on = 0.15
            else:
                on = 1.0 if ((int(v * 22) + int((u + 0.5) * 14)) % 2 == 0) else 0.45
            borde = min(1.0, (1.0 - abs(dx)) * 6.0)
            val = on * borde * rs.uniform(0.75, 1.0)
            px[y * N + x] = max(0, min(255, int(val * 255)))
    os.makedirs(os.path.dirname(PNG), exist_ok=True)
    png_gris(PNG, N, N, px)
    t = unreal.AssetImportTask()
    t.filename = PNG
    t.destination_path = TEX
    t.destination_name = 'T_Huella'
    t.automated = True
    t.replace_existing = True
    t.save = True
    tools.import_asset_tasks([t])
    tx = unreal.load_asset(TEX + '/T_Huella')
    if tx:
        tx.set_editor_property('srgb', False)
        tx.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_GRAYSCALE)
        tx.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
        tx.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
        eal.save_loaded_asset(tx, False)
    w('T_Huella: %s' % (tx.get_path_name() if tx else 'NO SE IMPORTO'))
    return tx


def material(tx):
    ruta = DM + '/M_Huella'
    if eal.does_asset_exist(ruta):
        eal.delete_asset(ruta)
    m = tools.create_asset('M_Huella', DM, unreal.Material, unreal.MaterialFactoryNew())
    # la mezcla antes que el dominio (si no, «Failed to compile»: tanda 23)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MODULATE)
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
    fallos = []
    def une(a, sa, b, eb):
        if not mel.connect_material_expressions(a, sa, b, eb):
            fallos.append('%s.%s > %s.%s' % (a.get_name(), sa, b.get_name(), eb))
    def esc(nombre, valor, x, y):
        e = E(unreal.MaterialExpressionScalarParameter, x, y)
        e.set_editor_property('parameter_name', nombre)
        e.set_editor_property('default_value', valor)
        return e
    def col(nombre, c, x, y):
        e = E(unreal.MaterialExpressionVectorParameter, x, y)
        e.set_editor_property('parameter_name', nombre)
        e.set_editor_property('default_value', unreal.LinearColor(c[0], c[1], c[2], 1.0))
        return e
    # UV, o con U y V cambiadas (Girar)
    uv = E(unreal.MaterialExpressionTextureCoordinate, -1100, 0)
    mu = E(unreal.MaterialExpressionComponentMask, -950, 80); mu.set_editor_property('r', True); mu.set_editor_property('g', False)
    mv = E(unreal.MaterialExpressionComponentMask, -950, 160); mv.set_editor_property('r', False); mv.set_editor_property('g', True)   # un canal cada una (por defecto R y G: float4 al unirlas)
    une(uv, '', mu, ''); une(uv, '', mv, '')
    sw = E(unreal.MaterialExpressionAppendVector, -800, 120)
    une(mv, '', sw, 'A'); une(mu, '', sw, 'B')
    girar = esc('Girar', 0.0, -800, 260)
    luv = E(unreal.MaterialExpressionLinearInterpolate, -650, 60)
    une(uv, '', luv, 'A'); une(sw, '', luv, 'B'); une(girar, '', luv, 'Alpha')
    ts = E(unreal.MaterialExpressionTextureSample, -480, 0)
    ts.set_editor_property('texture', tx)
    ts.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)   # la textura no es sRGB
    une(luv, '', ts, 'UVs')
    fuerza = esc('Fuerza', 1.0, -480, 220)
    mojada = esc('Mojada', 0.0, -480, 320)
    # opacidad: mascara x fuerza x (mojada: algo mas tenue)
    tenue = E(unreal.MaterialExpressionLinearInterpolate, -300, 300)
    c1 = E(unreal.MaterialExpressionConstant, -480, 420); c1.set_editor_property('r', 1.0)
    c2 = E(unreal.MaterialExpressionConstant, -480, 480); c2.set_editor_property('r', 0.9)   # tanda D: con 0,6 las mojadas casi no se veian en la grava
    une(c1, '', tenue, 'A'); une(c2, '', tenue, 'B'); une(mojada, '', tenue, 'Alpha')
    m1 = E(unreal.MaterialExpressionMultiply, -300, 100); une(ts, 'R', m1, 'A'); une(fuerza, '', m1, 'B')
    m2 = E(unreal.MaterialExpressionMultiply, -150, 150); une(m1, '', m2, 'A'); une(tenue, '', m2, 'B')
    mel.connect_material_property(m2, '', unreal.MaterialProperty.MP_OPACITY)
    # color: barro pardo oscuro o agua casi negra
    barro = col('Color', (0.035, 0.026, 0.018), -300, -200)
    agua = col('ColorMojada', (0.012, 0.012, 0.012), -300, -100)
    lc = E(unreal.MaterialExpressionLinearInterpolate, -150, -150)
    une(barro, '', lc, 'A'); une(agua, '', lc, 'B'); une(mojada, '', lc, 'Alpha')
    mel.connect_material_property(lc, '', unreal.MaterialProperty.MP_BASE_COLOR)
    mel.recompile_material(m)
    eal.save_loaded_asset(m, False)
    w('M_Huella: modulado, decal; fallos de conexion: %s' % (fallos or 'ninguno'))
    return m


tx = textura()
if tx:
    material(tx)
open(r'D:\LostHorizon\huellas_info.txt', 'w', encoding='utf-8').write('\n'.join(L))
