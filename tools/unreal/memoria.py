"""Inventario de la memoria de vídeo que piden las texturas del proyecto (tanda 23).

La GTX 1050 Ti tiene 4 GB y con el editor abierto la tarjeta anda por 3,6-3,7 GB (tools/unreal/medir.py mide toda la
tarjeta: editor, Windows y juego). Para decidir qué se puede recortar hace falta saber qué pesa cada cosa, y eso no lo
da la medida de la tarjeta. Este script no cambia nada: recorre las texturas de /Game y apunta de cada una el tamaño,
el formato, lo que ocupa con todos sus niveles de detalle cargados, quién la usa y lo que se ahorraría limitándola a 1K.

Uso (en el editor):  py tools/unreal/memoria.py
Salida: un resumen en el registro (líneas «[Tarsis] memoria: ...») y la lista completa en Saved/Tarsis/memoria.json.

Lo que ocupa una textura se calcula del tamaño y del formato de compresión (bits por píxel, más un tercio por los niveles
de detalle); si el motor sabe decir lo que tiene cargado ahora mismo, se apunta también («cargado»).
"""
import os, json
import unreal

eal = unreal.EditorAssetLibrary


def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))


def _prop(o, nombre, defecto=None):
    try:
        return o.get_editor_property(nombre)
    except Exception:
        return defecto


def _bpp(tx):
    """Bits por píxel del formato con el que la textura llega a la tarjeta en PC (DXT/BC)."""
    cs = str(_prop(tx, 'compression_settings', '')).upper()
    if 'NORMALMAP' in cs:
        return 8, 'BC5'
    if 'HDR' in cs:
        return 64, 'RGBA16F'
    if 'BC7' in cs:
        return 8, 'BC7'
    if 'GRAYSCALE' in cs or 'ALPHA' in cs or 'DISPLACEMENT' in cs:
        return 8, 'G8'
    if 'VECTOR' in cs or 'USERINTERFACE' in cs or 'EDITORICON' in cs:
        return 32, 'BGRA8'
    alfa = False
    try:
        alfa = bool(tx.has_alpha_channel())
    except Exception:
        pass
    if _prop(tx, 'compression_no_alpha', False):
        alfa = False
    return (8, 'BC3') if alfa else (4, 'BC1')


def _lado(tx):
    try:
        x, y = int(tx.blueprint_get_size_x()), int(tx.blueprint_get_size_y())
    except Exception:
        return 0, 0
    tope = int(_prop(tx, 'max_texture_size', 0) or 0)
    while tope and max(x, y) > tope:
        x, y = max(1, x // 2), max(1, y // 2)
    for _ in range(max(0, int(_prop(tx, 'lod_bias', 0) or 0))):
        x, y = max(1, x // 2), max(1, y // 2)
    return x, y


def _cargado(tx):
    for fn in ('blueprint_get_memory_size',):
        try:
            return int(getattr(tx, fn)())
        except Exception:
            pass
    return None


def inventario():
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    opciones = None
    try:
        opciones = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
    except Exception:
        pass
    filas = []
    for ad in ar.get_assets_by_path('/Game', recursive=True):
        if str(ad.asset_class_path.asset_name) != 'Texture2D':
            continue
        tx = ad.get_asset()
        if tx is None:
            continue
        x, y = _lado(tx)
        bpp, fmt = _bpp(tx)
        sin_mips = 'NOMIPMAPS' in str(_prop(tx, 'mip_gen_settings', '')).upper()
        total = int(x * y * bpp / 8 * (1.0 if sin_mips else 4.0 / 3.0))
        usos = None
        if opciones is not None:
            try:
                usos = [str(r) for r in (ar.get_referencers(ad.package_name, opciones) or [])]
            except Exception:
                usos = None
        a1k = total
        if max(x, y) > 1024:
            k = (1024.0 / max(x, y)) ** 2
            a1k = int(total * k)
        filas.append({'ruta': str(ad.package_name), 'lado': [x, y], 'formato': fmt, 'bytes': total, 'cargado': _cargado(tx),
                      'usos': None if usos is None else len(usos), 'usa': (usos or [])[:6], 'ahorro_1k': total - a1k,
                      'tope': int(_prop(tx, 'max_texture_size', 0) or 0)})
    filas.sort(key=lambda f: -f['bytes'])
    return filas


def resumen(filas, n=25):
    mb = lambda b: '%.1f' % (b / 1048576.0)
    total = sum(f['bytes'] for f in filas)
    carg = [f['cargado'] for f in filas if f['cargado'] is not None]
    sin_uso = [f for f in filas if f['usos'] == 0]
    grandes = [f for f in filas if max(f['lado']) > 1024]
    log('memoria: %d texturas, %s MB con todo cargado%s' % (len(filas), mb(total), (' (%s MB cargados ahora)' % mb(sum(carg))) if carg else ''))
    log('memoria: %d de más de 1K piden %s MB; limitarlas todas a 1K ahorraría %s MB' % (len(grandes), mb(sum(f['bytes'] for f in grandes)), mb(sum(f['ahorro_1k'] for f in grandes))))
    log('memoria: %d sin nadie que las use (%s MB): %s' % (len(sin_uso), mb(sum(f['bytes'] for f in sin_uso)), ', '.join(f['ruta'].split('/')[-1] for f in sin_uso[:12])))
    por_carpeta = {}
    for f in filas:
        c = '/'.join(f['ruta'].split('/')[:4])
        por_carpeta[c] = por_carpeta.get(c, 0) + f['bytes']
    for c, b in sorted(por_carpeta.items(), key=lambda kv: -kv[1])[:10]:
        log('memoria: carpeta %s: %s MB' % (c, mb(b)))
    for f in filas[:n]:
        log('memoria: %6s MB  %4dx%-4d %-7s usos %s  %s' % (mb(f['bytes']), f['lado'][0], f['lado'][1], f['formato'], '?' if f['usos'] is None else f['usos'], f['ruta']))
    return {'texturas': len(filas), 'mb': round(total / 1048576.0, 1), 'mb_mas_de_1k': round(sum(f['bytes'] for f in grandes) / 1048576.0, 1),
            'ahorro_1k_mb': round(sum(f['ahorro_1k'] for f in grandes) / 1048576.0, 1), 'sin_uso': len(sin_uso),
            'sin_uso_mb': round(sum(f['bytes'] for f in sin_uso) / 1048576.0, 1)}


def todo():
    filas = inventario()
    r = resumen(filas)
    try:
        d = os.path.join(unreal.Paths.project_saved_dir(), 'Tarsis')
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'memoria.json'), 'w', encoding='utf-8') as fh:
            json.dump({'resumen': r, 'texturas': filas}, fh, indent=1, ensure_ascii=False)
        log('memoria: lista completa en', os.path.join(d, 'memoria.json'))
    except Exception as e:
        log('AVISO: memoria: no se escribió la lista:', repr(e))
    return r


if __name__ == '__main__':
    todo()
