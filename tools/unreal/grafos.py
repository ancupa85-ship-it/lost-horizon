"""Lectura de grafos de Blueprint desde Python (5.8), común a gasp_guardia.py y gasp_cuttlas.py.

Los nodos se sacan con unreal.ObjectIterator (EdGraph.Nodes está protegida) y sus conexiones con
BlueprintGraphPin.list_connected_pins. La salida va a la lista L (w() añade una línea); quien escribe el informe la vuelca.
"""
import re
import unreal

BEL = unreal.BlueprintEditorLibrary
L = []


def w(s=''):
    L.append(s)


def corta(s, n=160):
    s = str(s).replace('\n', ' ')
    return s if len(s) <= n else s[:n - 1] + '…'


# ------------------------------------------------------------------ lectura de grafos
_NODOS = {}


def nodos_por_grafo():
    """outer (EdGraph) -> nodos, de una pasada por todos los EdGraphNode cargados (se rehace con nodos_de si falta)."""
    if not _NODOS:
        for n in unreal.ObjectIterator(unreal.EdGraphNode):
            try:
                _NODOS.setdefault(n.get_outer().get_path_name(), []).append(n)
            except Exception:
                pass
    return _NODOS


def nodos_de(g):
    k = g.get_path_name()
    if k not in nodos_por_grafo():
        _NODOS.clear()   # se cargó otro blueprint después de la última pasada
        nodos_por_grafo()
        _NODOS.setdefault(k, [])   # grafo vacío: que no vuelva a rehacer la pasada
    return _NODOS[k]


def titulo(n):
    try:
        t = str(BEL.get_node_title(n)) if isinstance(n, unreal.K2Node) else n.get_name()
    except Exception:
        t = n.get_name()
    return t.replace('\n', ' ').strip()


def pines(n):
    try:
        return list(BEL.list_all_pins(n))
    except Exception:
        return []


def tipo_txt(p):
    try:
        return str(p.get_pin_type().export_text())
    except Exception:
        return ''


def es_exec(p):
    # el texto visible del tipo va traducido (editor en español): se mira la categoría interna
    return bool(re.search(r'PinCategory="?exec"?[,)]', tipo_txt(p)))


def es_salida(p):
    return p.get_pin_direction() == unreal.EdGraphPinDirection.EGPD_OUTPUT


def nombre(p):
    return str(p.get_pin_name())


def conectados(p):
    try:
        return list(p.list_connected_pins())
    except Exception:
        return []


def es_puro(n):
    return not any(es_exec(p) for p in pines(n))


def expr(p, prof=2):
    """Valor de un pin de entrada: de qué nodo viene (con sus entradas si es puro) o su valor por defecto."""
    c = conectados(p)
    if not c:
        v = ''
        try:
            v = str(p.get_pin_value())
        except Exception:
            pass
        return v if v not in ('', 'None') else '∅'
    src = c[0]
    n = src.get_owning_node()
    t = titulo(n)
    sal = [q for q in pines(n) if es_salida(q) and not es_exec(q)]
    extra = ('.' + nombre(src)) if len(sal) > 1 or nombre(src) not in ('ReturnValue', 'Return Value', '') else ''
    if es_puro(n) and prof > 0:
        args = [q for q in pines(n) if not es_salida(q) and not es_exec(q) and nombre(q) != 'self']
        if args:
            return '%s(%s)%s' % (t, ', '.join('%s=%s' % (nombre(q), expr(q, prof - 1)) for q in args), extra)
    return '%s%s' % (t, extra)


def sentencia(n):
    ent = [p for p in pines(n) if not es_salida(p) and not es_exec(p) and nombre(p) not in ('self',)]
    partes = []
    for p in ent:
        v = expr(p, 2)
        if v != '∅':
            partes.append('%s=%s' % (nombre(p), v))
    return titulo(n) + (' (' + '; '.join(partes) + ')' if partes else '')


def flujo(pin, sangria, vistos, cuenta, maximo=80):
    for dst in conectados(pin):
        if cuenta[0] >= maximo:
            if cuenta[0] == maximo:
                w(sangria + '… (corto aquí)')
                cuenta[0] += 1
            return
        n = dst.get_owning_node()
        clave = n.get_path_name()
        if clave in vistos:
            w(sangria + '↺ ' + titulo(n))
            continue
        vistos.add(clave)
        cuenta[0] += 1
        w(sangria + '- ' + corta(sentencia(n), 400))
        salidas = [p for p in pines(n) if es_salida(p) and es_exec(p)]
        for p in salidas:
            if len(salidas) > 1:
                if conectados(p):
                    w(sangria + '  [' + nombre(p) + ']')
                    flujo(p, sangria + '    ', vistos, cuenta, maximo)
            else:
                flujo(p, sangria, vistos, cuenta, maximo)


def entradas(grafo):
    """Nodos de entrada de un grafo: con salida exec y sin entrada exec (eventos, entradas de función, input)."""
    r = []
    for n in nodos_de(grafo):
        ps = pines(n)
        if any(es_exec(p) and es_salida(p) for p in ps) and not any(es_exec(p) and not es_salida(p) for p in ps):
            r.append(n)
    return r


def volcar_grafo(grafo, maximo=80, filtro=None):
    w('  ## grafo %s' % grafo.get_name())
    for e in entradas(grafo):
        t = titulo(e)
        if filtro and not re.search(filtro, t, re.I):
            continue
        datos_e = [nombre(p) for p in pines(e) if es_salida(p) and not es_exec(p)]
        w('  * %s%s' % (t, (' -> ' + ', '.join(datos_e)) if datos_e else ''))
        vistos, cuenta = set(), [0]
        for p in pines(e):
            if es_exec(p) and es_salida(p):
                if nombre(p) not in ('then', 'Then', 'OutputDelegate', '') and len([q for q in pines(e) if es_exec(q) and es_salida(q)]) > 1:
                    if conectados(p):
                        w('    [' + nombre(p) + ']')
                        flujo(p, '      ', vistos, cuenta, maximo)
                else:
                    flujo(p, '    ', vistos, cuenta, maximo)


def enum_valores(f, e):
    """valor -> nombre interno (E_X::NewEnumeratorK) y nombre visible, leídos del .uasset del UserDefinedEnum."""
    t = open(f, 'rb').read().decode('latin-1')
    internos = list(dict.fromkeys(re.findall(re.escape(e) + r'::(NewEnumerator\d+)', t)))
    visibles = {}
    for m in re.finditer(r'DisplayNameMap\((\d+) - Value\)', t):
        ini = t.rfind('/Game/', 0, m.start())
        trozo = t[max(0, ini - 80):ini]
        cand = [c for c in re.findall(r'[A-Za-z][A-Za-z0-9 _\-]+', trozo) if not re.fullmatch(r'[0-9A-F]{16,}', c)]
        if cand:
            visibles[int(m.group(1))] = cand[-1]
    return ['%d = %s::%s "%s"' % (i, e, n, visibles.get(i, '?')) for i, n in enumerate(internos)]


def grafo(bp, nombre_g):
    for g in BEL.list_graphs(bp):
        if g.get_name() == nombre_g:
            return g
    return None
