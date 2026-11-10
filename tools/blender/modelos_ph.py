"""Descarga modelos 3D escaneados de Poly Haven (CC0) en glTF a assets/modelos-ph/<id>/ (no se guardan en el repositorio).
Uso: python3 tools/blender/modelos_ph.py [resolución de textura: 1k, 2k]"""
import json, os, sys, urllib.request
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); D = os.path.join(R, 'assets', 'modelos-ph')
IDS = ['wooden_military_crate', 'old_military_crate', 'wooden_crate_02', 'Barrel_01', 'Barrel_02', 'street_lamp_01', 'street_lamp_02', 'security_light',
       'industrial_wall_lamp', 'concrete_road_barrier', 'covered_car', 'ammo_box', 'power_box_01', 'utility_box_01', 'metal_jerrycan_green',
       'old_military_compressor', 'portable_generator', 'exterior_aircon_unit', 'old_tyre', 'rollershutter_door', 'modular_chainlink_fence',
       'modular_metal_gutter', 'portable_searchlight', 'modular_electricity_poles', 'trashbag', 'wooden_crate_01', 'barrel_03']
def get(url): return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'lost-horizon-build'}), timeout=180).read()
def fetch(res='1k'):
    for i in IDS:
        d = os.path.join(D, i); main = os.path.join(d, i + '.gltf')
        if os.path.exists(main): continue
        try:
            f = json.loads(get('https://api.polyhaven.com/files/' + i))['gltf']; f = f.get(res, f[sorted(f)[0]])['gltf']
            os.makedirs(d, exist_ok=True); tot = 0
            for path, inc in f.get('include', {}).items():
                p = os.path.join(d, path); os.makedirs(os.path.dirname(p), exist_ok=True); b = get(inc['url']); open(p, 'wb').write(b); tot += len(b)
            open(main, 'wb').write(get(f['url'])); print('  +', i, tot // 1024, 'KB', flush=True)
        except Exception as e: print('  FALLO', i, e, flush=True)
if __name__ == '__main__': fetch(sys.argv[1] if len(sys.argv) > 1 else '1k')
