#!/usr/bin/env python3
"""Monta el visor en tiempo real del escenario realista en un solo archivo: dist/visor/tarsis-escenario.html.
Antes: python3 tools/blender/texturas.py && python3 tools/blender/modelos_ph.py && LH_GLB=dist/visor/base.glb python3 tools/blender/escena_base.py"""
import os, base64, io, json
from PIL import Image
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); V = os.path.join(R, 'dist', 'visor'); TX = os.path.join(R, 'assets', 'texturas')
def rd(*p): return open(os.path.join(R, *p), encoding='utf-8').read()
def tex(f, size, q=72):
    im = Image.open(os.path.join(TX, f)).convert('RGB').resize((size, size), Image.LANCZOS); b = io.BytesIO(); im.save(b, 'JPEG', quality=q); return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
T = {'asphalt_diff': ('asphalt_02_diff.jpg', 1024), 'asphalt_nor': ('asphalt_02_nor.jpg', 512), 'asphalt_rough': ('asphalt_02_rough.jpg', 512),
     'concrete_diff': ('concrete_wall_008_diff.jpg', 1024), 'concrete_nor': ('concrete_wall_008_nor.jpg', 512), 'plaster_diff': ('painted_plaster_wall_diff.jpg', 512),
     'plaster_nor': ('painted_plaster_wall_nor.jpg', 512), 'wood_diff': ('wood_planks_dirt_diff.jpg', 512), 'rust_diff': ('rusty_metal_02_diff.jpg', 512),
     'green_diff': ('green_metal_rust_diff.jpg', 512), 'roof_diff': ('corrugated_iron_02_diff.jpg', 512), 'roof_nor': ('corrugated_iron_02_nor.jpg', 512), 'floor_diff': ('concrete_floor_worn_001_diff.jpg', 512)}
info = json.load(open(os.path.join(V, 'base.json')))
people = {q['name']: base64.b64encode(open(os.path.join(R, 'assets', 'modelos-ph', 'persona_' + q['name'], 'persona_' + q['name'] + '_anim.glb'), 'rb').read()).decode() for q in info.get('people', [])}
data = {'info': info, 'people': people, 'glb': base64.b64encode(open(os.path.join(V, 'base.glb'), 'rb').read()).decode(), 'tex': {k: tex(*v) for k, v in T.items()}}
post = '\n'.join(rd('vendor', 'post', f + '.js') for f in ('CopyShader', 'LuminosityHighPassShader', 'EffectComposer', 'RenderPass', 'ShaderPass', 'UnrealBloomPass'))
out = (rd('escenario', 'visor.html') + '<script>\n' + rd('vendor', 'three.min.js') + '\n</script>\n<script>\n' + rd('vendor', 'GLTFLoader.js') + '\n' + post + '\n</script>\n'
       '<script>window.LH_ESC=' + json.dumps(data, separators=(',', ':')) + ';</script>\n<script>\n' + rd('escenario', 'visor.js') + '</script>\n')
p = os.path.join(V, 'tarsis-escenario.html'); open(p, 'w', encoding='utf-8').write(out); print('escrito', p, len(out) // 1024, 'KB')
