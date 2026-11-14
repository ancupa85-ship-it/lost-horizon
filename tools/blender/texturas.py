"""Descarga texturas PBR de Poly Haven (CC0) a assets/texturas/ (no se guardan en el repositorio).
Uso: python3 tools/blender/texturas.py [resolución]   (1k, 2k, 4k)"""
import json, os, sys, urllib.request
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); D = os.path.join(R, 'assets', 'texturas')
IDS = ['asphalt_02', 'concrete_wall_008', 'painted_plaster_wall', 'wood_planks_dirt', 'rusty_metal_02', 'green_metal_rust', 'corrugated_iron_02', 'concrete_floor_worn_001',
       'poly_wool_herringbone', 'rough_linen']   # tanda 18: mantas y colchones
MAPS = {'Diffuse': 'diff', 'nor_gl': 'nor', 'Rough': 'rough', 'Displacement': 'disp'}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'lost-horizon-build'}), timeout=120).read()
def fetch(res='2k'):
    os.makedirs(D, exist_ok=True)
    for i in IDS:
        files = None
        for k, short in MAPS.items():
            p = os.path.join(D, '%s_%s.jpg' % (i, short))
            if os.path.exists(p): continue
            files = files or json.loads(get('https://api.polyhaven.com/files/' + i))
            if k not in files: print('  sin', k, 'en', i); continue
            f = files[k].get(res, files[k][sorted(files[k])[0]]); f = f.get('jpg') or f[sorted(f)[0]]
            open(p, 'wb').write(get(f['url'])); print('  +', os.path.basename(p), os.path.getsize(p) // 1024, 'KB')
if __name__ == '__main__': fetch(sys.argv[1] if len(sys.argv) > 1 else '2k')
