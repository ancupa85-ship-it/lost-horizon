"""Comprueba las huellas de los muebles de dist/visor/base.json: que no pisen muros ni cajas, que no se monten
unos sobre otros y que dejen libre el paso de cada puerta (0,8 m a cada lado del eje, 2,6 m por delante y por detrás).
Uso: python3 tools/audit-muebles.py   (sale con código 1 si hay algo mal)"""
import json, math, os, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(R, 'dist', 'visor', 'base.json'))); MAP = d['map']; T = d['T']; bad = 0
def pts(o, n=5, grow=0.0):
    _, x, y, hx, hy, rz = o; c, s = math.cos(rz), math.sin(rz)
    for i in range(n):
        for j in range(n):
            u = (i / (n - 1) * 2 - 1) * (hx + grow); v = (j / (n - 1) * 2 - 1) * (hy + grow); yield x + u * c - v * s, -(y + u * s + v * c)   # → x, z del visor
def cell(x, z):
    tx, ty = int(x // T), int(z // T); return MAP[ty][tx] if 0 <= ty < len(MAP) and 0 <= tx < len(MAP[0]) else '#'
doors = []
for ty, row in enumerate(MAP):
    for tx, c in enumerate(row):
        if c in 'DLVb': doors.append((c, tx, ty, row[tx - 1] in 'W#' and row[tx + 1] in 'W#'))
for o in d['obst']:
    P = list(pts(o)); cs = {cell(x, z) for x, z in P} & set('#WTcgDLVb')
    if cs: bad += 1; print('PISA', ''.join(sorted(cs)), o)
    for c, tx, ty, horiz in doors:
        cx, cz = tx * T + T / 2, ty * T + T / 2
        if any((abs(x - cx) < 0.8 and abs(z - cz) < 2.6) if horiz else (abs(z - cz) < 0.8 and abs(x - cx) < 2.6) for x, z in pts(o, 7)):
            bad += 1; print('TAPA la puerta %s (%d,%d)' % (c, tx, ty), o)
O = d['obst']
for i in range(len(O)):
    for j in range(i + 1, len(O)):
        if math.hypot(O[i][1] - O[j][1], O[i][2] - O[j][2]) > 3: continue
        A = list(pts(O[i], 7)); _, x, y, hx, hy, rz = O[j]; c, s = math.cos(rz), math.sin(rz)
        if any(abs((px - x) * c + (-pz - y) * s) < hx and abs(-(px - x) * s + (-pz - y) * c) < hy for px, pz in A):
            bad += 1; print('SE MONTAN', O[i], O[j])
print('muebles', len(O), 'puertas', len(doors), 'fallos', bad); sys.exit(1 if bad else 0)
