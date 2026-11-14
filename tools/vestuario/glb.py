"""Lectura y escritura mínima de .glb (glTF 2.0 binario) con numpy: lo justo para añadir y quitar mallas con
esqueleto, materiales y texturas sin pasar el archivo por Blender (el esqueleto y las animaciones no se tocan)."""
import json, struct, io
import numpy as np

CT = {5120: 'i1', 5121: 'u1', 5122: 'i2', 5123: 'u2', 5125: 'u4', 5126: 'f4'}
CTI = {v: k for k, v in CT.items()}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


class Glb:
    def __init__(self, path):
        b = open(path, 'rb').read()
        assert b[:4] == b'glTF'
        n = struct.unpack('<I', b[12:16])[0]
        self.j = json.loads(b[20:20 + n])
        m = struct.unpack('<I', b[20 + n:24 + n])[0]
        self.views = []   # bytes de cada bufferView
        bn = b[28 + n:28 + n + m]
        for bv in self.j['bufferViews']:
            o = bv.get('byteOffset', 0)
            self.views.append(bytes(bn[o:o + bv['byteLength']]))

    # ---- lectura
    def acc(self, i):
        a = self.j['accessors'][i]
        bv = self.j['bufferViews'][a['bufferView']]
        n = NC[a['type']]
        dt = np.dtype('<' + CT[a['componentType']])
        st = bv.get('byteStride')
        assert not st or st == n * dt.itemsize, 'bufferView entrelazado'
        return np.frombuffer(self.views[a['bufferView']], dt, a['count'] * n, a.get('byteOffset', 0)).reshape(a['count'], n)

    # ---- escritura
    def add_view(self, data, target=None):
        bv = {'buffer': 0, 'byteLength': len(data)}
        if target:
            bv['target'] = target
        self.j['bufferViews'].append(bv)
        self.views.append(bytes(data))
        return len(self.views) - 1

    def add_acc(self, arr, typ, minmax=False, target=None):
        arr = np.ascontiguousarray(arr)
        a = {'bufferView': self.add_view(arr.tobytes(), target), 'componentType': CTI[arr.dtype.str[1:]],
             'count': int(arr.shape[0]), 'type': typ}
        if minmax:
            a['min'] = [float(x) for x in arr.reshape(arr.shape[0], -1).min(0)]
            a['max'] = [float(x) for x in arr.reshape(arr.shape[0], -1).max(0)]
        self.j['accessors'].append(a)
        return len(self.j['accessors']) - 1

    def add_image(self, pil, name, jpeg=82):
        f = io.BytesIO()
        if jpeg:
            pil.convert('RGB').save(f, 'JPEG', quality=jpeg)
        else:
            pil.save(f, 'PNG', optimize=True)
        self.j['images'].append({'bufferView': self.add_view(f.getvalue()), 'mimeType': 'image/jpeg' if jpeg else 'image/png', 'name': name})
        if not self.j.get('samplers'):
            self.j['samplers'] = [{'magFilter': 9729, 'minFilter': 9987}]
        self.j['textures'].append({'sampler': 0, 'source': len(self.j['images']) - 1})
        return len(self.j['textures']) - 1

    def set_image(self, idx, pil, jpeg=85):
        f = io.BytesIO()
        pil.convert('RGB').save(f, 'JPEG', quality=jpeg)
        im = self.j['images'][idx]
        im['bufferView'] = self.add_view(f.getvalue())
        im['mimeType'] = 'image/jpeg'

    def image(self, idx):
        from PIL import Image
        return Image.open(io.BytesIO(self.views[self.j['images'][idx]['bufferView']]))

    def add_material(self, name, color=None, tex=None, normal=None, rough=0.8, metal=0.0, double=False, nscale=1.0):
        pbr = {'metallicFactor': metal, 'roughnessFactor': rough}
        if color is not None:
            pbr['baseColorFactor'] = [float(c) for c in color] + [1.0] * (4 - len(color))
        if tex is not None:
            pbr['baseColorTexture'] = {'index': tex}
        m = {'name': name, 'pbrMetallicRoughness': pbr}
        if normal is not None:
            m['normalTexture'] = {'index': normal, 'scale': nscale}
        if double:
            m['doubleSided'] = True
        self.j['materials'].append(m)
        return len(self.j['materials']) - 1

    def add_skinned_mesh(self, name, P, N, UV, J, W, T, material, parent, skin=0):
        """P, N en espacio glTF (Y arriba); J u8 (n,4); W f32 (n,4); T índices (m,3)."""
        prim = {'attributes': {
            'POSITION': self.add_acc(P.astype('<f4'), 'VEC3', True, 34962), 'NORMAL': self.add_acc(N.astype('<f4'), 'VEC3', False, 34962),
            'TEXCOORD_0': self.add_acc(UV.astype('<f4'), 'VEC2', False, 34962), 'JOINTS_0': self.add_acc(J.astype('u1'), 'VEC4', False, 34962),
            'WEIGHTS_0': self.add_acc(W.astype('<f4'), 'VEC4', False, 34962)},
            'indices': self.add_acc(T.astype('<u2' if len(P) < 65535 else '<u4').reshape(-1, 1), 'SCALAR', False, 34963), 'material': material}
        self.j['meshes'].append({'name': name, 'primitives': [prim]})
        self.j['nodes'].append({'mesh': len(self.j['meshes']) - 1, 'name': name, 'skin': skin})
        self.j['nodes'][parent].setdefault('children', []).append(len(self.j['nodes']) - 1)

    def remove_mesh_nodes(self, pred):
        """Quita los nodos con malla cuyo nombre cumple pred (y reindexa todo lo que apunta a nodos)."""
        j = self.j
        drop = [i for i, n in enumerate(j['nodes']) if 'mesh' in n and pred(n['name'])]
        if not drop:
            return []
        keep = [i for i in range(len(j['nodes'])) if i not in drop]
        mp = {o: k for k, o in enumerate(keep)}
        names = [j['nodes'][i]['name'] for i in drop]
        j['nodes'] = [j['nodes'][i] for i in keep]
        for n in j['nodes']:
            if 'children' in n:
                n['children'] = [mp[c] for c in n['children'] if c in mp]
        for s in j['scenes']:
            s['nodes'] = [mp[c] for c in s['nodes'] if c in mp]
        for s in j['skins']:
            s['joints'] = [mp[c] for c in s['joints']]
            if 'skeleton' in s:
                s['skeleton'] = mp[s['skeleton']]
        for a in j.get('animations', []):
            a['channels'] = [c for c in a['channels'] if c['target'].get('node') in mp]
            for c in a['channels']:
                c['target']['node'] = mp[c['target']['node']]
        return names

    def gc(self):
        """Quita mallas, materiales, texturas, imágenes, accesores y vistas que ya nadie usa, y reindexa."""
        j = self.j

        def compact(key, used):
            keep = sorted(used)
            mp = {o: k for k, o in enumerate(keep)}
            j[key] = [j[key][i] for i in keep]
            return mp
        mm = compact('meshes', {n['mesh'] for n in j['nodes'] if 'mesh' in n})
        for n in j['nodes']:
            if 'mesh' in n:
                n['mesh'] = mm[n['mesh']]
        prims = [p for m in j['meshes'] for p in m['primitives']]
        mt = compact('materials', {p['material'] for p in prims if 'material' in p})
        for p in prims:
            if 'material' in p:
                p['material'] = mt[p['material']]

        def texrefs(m):
            out = []
            pbr = m.get('pbrMetallicRoughness', {})
            for d in (pbr.get('baseColorTexture'), pbr.get('metallicRoughnessTexture'), m.get('normalTexture'), m.get('occlusionTexture'), m.get('emissiveTexture')):
                if d:
                    out.append(d)
            for e in m.get('extensions', {}).values():
                for v in e.values():
                    if isinstance(v, dict) and 'index' in v:
                        out.append(v)
            return out
        refs = [r for m in j['materials'] for r in texrefs(m)]
        tx = compact('textures', {r['index'] for r in refs})
        for r in refs:
            r['index'] = tx[r['index']]
        im = compact('images', {t['source'] for t in j['textures']})
        for t in j['textures']:
            t['source'] = im[t['source']]
        used = set()
        for p in prims:
            used |= set(p['attributes'].values())
            if 'indices' in p:
                used.add(p['indices'])
        for s in j['skins']:
            if 'inverseBindMatrices' in s:
                used.add(s['inverseBindMatrices'])
        for a in j.get('animations', []):
            for s in a['samplers']:
                used |= {s['input'], s['output']}
        ac = compact('accessors', used)
        for p in prims:
            p['attributes'] = {k: ac[v] for k, v in p['attributes'].items()}
            if 'indices' in p:
                p['indices'] = ac[p['indices']]
        for s in j['skins']:
            if 'inverseBindMatrices' in s:
                s['inverseBindMatrices'] = ac[s['inverseBindMatrices']]
        for a in j.get('animations', []):
            for s in a['samplers']:
                s['input'], s['output'] = ac[s['input']], ac[s['output']]
        usedv = {a['bufferView'] for a in j['accessors']} | {i['bufferView'] for i in j['images'] if 'bufferView' in i}
        keep = sorted(usedv)
        bv = {o: k for k, o in enumerate(keep)}
        j['bufferViews'] = [j['bufferViews'][i] for i in keep]
        self.views = [self.views[i] for i in keep]
        for a in j['accessors']:
            a['bufferView'] = bv[a['bufferView']]
        for i in j['images']:
            if 'bufferView' in i:
                i['bufferView'] = bv[i['bufferView']]

    def save(self, path):
        self.gc()
        j = self.j
        blob = bytearray()
        for bv, data in zip(j['bufferViews'], self.views):
            while len(blob) % 4:
                blob.append(0)
            bv['byteOffset'] = len(blob)
            bv['byteLength'] = len(data)
            blob += data
        while len(blob) % 4:
            blob.append(0)
        j['buffers'] = [{'byteLength': len(blob)}]
        js = json.dumps(j, separators=(',', ':')).encode()
        js += b' ' * (-len(js) % 4)
        out = b'glTF' + struct.pack('<II', 2, 28 + len(js) + len(blob)) + struct.pack('<I4s', len(js), b'JSON') + js + struct.pack('<I4s', len(blob), b'BIN\x00') + bytes(blob)
        open(path, 'wb').write(out)
        return len(out)
