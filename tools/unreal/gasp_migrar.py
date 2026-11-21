"""Migración del Game Animation Sample (GASP) a Tarsis (D:\\PruebaLumen\\PruebaLumen), tanda A de animación.

Tres modos (variable de entorno LH_GASP_MODO):
  seco      (por defecto) se lanza en el GASP. Calcula el cierre de dependencias duras y blandas de las raíces, sus MB
            por carpeta, los plugins que exige (por los módulos /Script/* y los puntos de montaje de plugin), qué rutas
            ya existen en el Content de Tarsis y qué cosas no queremos (mapas, MetaHumans, traversal, smart objects,
            texturas grandes) indicando si entran por referencia dura o solo blanda. Escribe gasp_migrar.txt y
            gasp_migrar.json (lista de paquetes) junto a LH_GASP_MIGRAR_SALIDA (D:\\LostHorizon por defecto).
  copiar    sin Unreal (python normal o el de Unreal): lee gasp_migrar.json, comprueba que no hay choques ni editor
            de Tarsis abierto, hace PruebaLumen.uproject.bak, añade los plugins que faltan y copia .uasset/.uexp/
            .ubulk/.uptnl a las mismas rutas del Content de Tarsis. Solo copia los paquetes del cierre DURO salvo que
            LH_GASP_BLANDAS=1.
  comprobar se lanza en Tarsis. Carga y compila SandboxCharacter_CMC_ABP y cuenta las bases de Pose Search que ve
            el registro.

    D:\\ue_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe "D:\\GASP\\GameAnimationSample.uproject" -run=pythonscript -script="<repo>\\tools\\unreal\\gasp_migrar.py" -unattended -nosplash -nullrhi
"""
import json
import os
import re
import shutil
import sys

MODO = os.environ.get('LH_GASP_MODO', 'seco')
DIR = os.environ.get('LH_GASP_MIGRAR_SALIDA') or r'D:\LostHorizon'
TXT = os.path.join(DIR, 'gasp_migrar.txt')
JSN = os.path.join(DIR, 'gasp_migrar.json')
GASP = r'D:\GASP'
TARSIS = r'D:\PruebaLumen\PruebaLumen'
UPROJECT = os.path.join(TARSIS, 'PruebaLumen.uproject')
MOTOR = r'D:\ue_5.8\Engine'

RAICES = ['/Game/Blueprints/SandboxCharacter_CMC',
          '/Game/Blueprints/SandboxCharacter_CMC_ABP',
          '/Game/Blueprints/RetargetedCharacters/ABP_GenericRetarget',
          '/Game/Characters/UEFN_Mannequin/Rigs/IK_UEFN_Mannequin',
          '/Game/Characters/UE5_Mannequins/Rigs/RTG_UEFN_to_UE5_Mannequin']
EXT = ('.uasset', '.umap', '.uexp', '.ubulk', '.uptnl')
# lo que no queremos arrastrar
NO_QUEREMOS = [('mapa', lambda p, c: c == 'World'),
               ('MetaHumans', lambda p, c: p.startswith('/Game/MetaHumans/')),
               ('niveles', lambda p, c: p.startswith('/Game/Levels/')),
               ('traversal', lambda p, c: 'traversal' in p.lower()),
               ('smart objects', lambda p, c: 'smartobject' in p.lower().replace('_', '')),
               ('ejemplos aislados', lambda p, c: p.startswith('/Game/IsolatedExamples/')),
               ('Paragon/Echo', lambda p, c: '/Paragon/' in p or '/Echo/' in p)]


def ficheros(raiz_content, paquete):
    base = os.path.join(raiz_content, paquete[len('/Game/'):].replace('/', os.sep))
    return [base + e for e in EXT if os.path.exists(base + e)]


def mb(n):
    return n / 1048576.0


def json_tolerante(ruta):
    """Los .uplugin de Epic a veces llevan comas finales (p. ej. DrawDebugLibrary), que json no acepta."""
    t = open(ruta, encoding='utf-8-sig').read()
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', t))


def plugins_del_motor():
    """módulo -> plugin, punto de montaje -> plugin, y los plugins activos por defecto, leyendo los .uplugin."""
    mod, montaje, por_defecto = {}, {}, set()
    for carpeta in (os.path.join(MOTOR, 'Plugins'), os.path.join(GASP, 'Plugins')):
        for raiz, dirs, archivos in os.walk(carpeta):
            for a in archivos:
                if not a.endswith('.uplugin'):
                    continue
                nombre = a[:-len('.uplugin')]
                try:
                    d = json_tolerante(os.path.join(raiz, a))
                except Exception:
                    continue
                for m in d.get('Modules', []):
                    mod[m.get('Name')] = nombre
                if d.get('CanContainContent'):
                    montaje[nombre] = nombre
                if d.get('EnabledByDefault'):
                    por_defecto.add(nombre)
            # no hace falta bajar a Binaries/Intermediate/Content
            dirs[:] = [x for x in dirs if x not in ('Binaries', 'Intermediate', 'Content', 'Resources', 'Source', 'Shaders')]
    return mod, montaje, por_defecto


def plugins_uproject(ruta):
    d = json.load(open(ruta, encoding='utf-8-sig'))
    return d, {p['Name']: p.get('Enabled', False) for p in d.get('Plugins', [])}


# ======================================================================== seco (dentro del GASP)
def seco():
    import unreal
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    L = []
    w = L.append

    def clase(p):
        a = reg.get_assets_by_package_name(p)
        return str(a[0].asset_class_path.asset_name) if a else '?'

    def deps(p, duras, blandas):
        o = unreal.AssetRegistryDependencyOptions(include_soft_package_references=blandas,
                                                  include_hard_package_references=duras)
        try:
            return [str(x) for x in reg.get_dependencies(p, o) or []]
        except Exception:
            return []

    def cierre(solo_duras):
        visto, padre, scripts, pila = set(), {}, set(), list(RAICES)
        while pila:
            p = pila.pop()
            if p in visto:
                continue
            visto.add(p)
            for d in deps(p, True, not solo_duras):
                if d.startswith('/Script/'):
                    scripts.add(d)
                elif d not in visto:
                    padre.setdefault(d, p)
                    pila.append(d)
        return visto, padre, scripts

    todo, padre, scripts = cierre(False)
    duro, padre_duro, scripts_duros = cierre(True)
    solo_blando = todo - duro
    content_gasp = os.path.join(GASP, 'Content')
    content_tarsis = os.path.join(TARSIS, 'Content')

    info = {}
    for p in sorted(todo):
        if p.startswith('/Game/'):
            fs = ficheros(content_gasp, p)
            ya = ficheros(content_tarsis, p)
            # choca si Tarsis tiene ese paquete y no es la copia idéntica que hizo este script
            igual = len(ya) == len(fs) and all(os.path.getsize(a) == os.path.getsize(b) for a, b in zip(sorted(ya), sorted(fs)))
            info[p] = {'clase': clase(p), 'bytes': sum(os.path.getsize(f) for f in fs), 'duro': p in duro,
                       'ficheros': [os.path.relpath(f, content_gasp) for f in fs],
                       'choca': bool(ya) and not igual, 'ya_copiado': bool(ya) and igual}
    otros = sorted(p for p in todo if not p.startswith('/Game/'))

    w('GASP -> Tarsis: migración en seco (gasp_migrar.py, modo seco)')
    w('Raíces: ' + ', '.join(RAICES))
    tot = sum(v['bytes'] for v in info.values())
    tot_duro = sum(v['bytes'] for v in info.values() if v['duro'])
    w('Cierre duro+blando: %d paquetes /Game, %.1f MB.  Solo duro: %d paquetes, %.1f MB.  Entran solo por blandas: %d (%.1f MB)'
      % (len(info), mb(tot), sum(1 for v in info.values() if v['duro']), mb(tot_duro),
         sum(1 for v in info.values() if not v['duro']), mb(tot - tot_duro)))
    w('')
    w('=== Por carpeta (tres niveles), duro+blando | solo duro')
    carp = {}
    for p, v in info.items():
        k = '/'.join(p.split('/')[:4])
        c = carp.setdefault(k, [0, 0, 0, 0])
        c[0] += 1
        c[1] += v['bytes']
        if v['duro']:
            c[2] += 1
            c[3] += v['bytes']
    for k in sorted(carp, key=lambda x: -carp[x][1]):
        c = carp[k]
        w('  %-60s %5d paq %8.1f MB | %5d paq %8.1f MB' % (k, c[0], mb(c[1]), c[2], mb(c[3])))
    w('')
    w('=== Por clase (duro+blando)')
    cl = {}
    for v in info.values():
        c = cl.setdefault(v['clase'], [0, 0])
        c[0] += 1
        c[1] += v['bytes']
    for k in sorted(cl, key=lambda x: -cl[x][1]):
        w('  %-32s %5d paq %8.1f MB' % (k, cl[k][0], mb(cl[k][1])))

    # plugins
    mod, montaje, por_defecto = plugins_del_motor()
    necesita, por_duro = {}, set()
    for s in sorted(scripts):
        m = s[len('/Script/'):]
        pl = mod.get(m)
        necesita.setdefault(pl or '(motor)', []).append(m + ('' if s in scripts_duros else ' [solo blanda]'))
        if s in scripts_duros:
            por_duro.add(pl or '(motor)')
    for p in otros:
        raiz = p.split('/')[1]
        if raiz in ('Engine',):
            continue
        pl = montaje.get(raiz, raiz)
        lista_pl = necesita.setdefault(pl, [])
        etiqueta_c = 'contenido /%s' % raiz + ('' if p in duro else ' [solo blanda]')
        if etiqueta_c not in lista_pl:
            lista_pl.append(etiqueta_c)
        if p in duro:
            por_duro.add(pl)
    _, en_tarsis = plugins_uproject(UPROJECT)
    _, en_gasp = plugins_uproject(os.path.join(GASP, 'GameAnimationSample.uproject'))
    w('')
    w('=== Plugins que exige el cierre (módulos /Script y contenido de plugin)')
    faltan = []
    for pl in sorted(necesita, key=lambda x: (x == '(motor)', x)):
        if pl == '(motor)':
            estado = 'módulos del motor, no hace falta plugin'
        elif en_tarsis.get(pl):
            estado = 'ya activo en PruebaLumen.uproject'
        elif pl in por_defecto:
            estado = 'activo por defecto en el motor'
        else:
            estado = 'FALTA en PruebaLumen.uproject' + (' (está en el GASP)' if en_gasp.get(pl) else '')
            if pl not in por_duro:
                estado += ' [solo blandas]'
            faltan.append(pl)
        w('  %-28s %-60s %s' % (pl, estado, ', '.join(sorted(necesita[pl]))[:300]))
    faltan_duros = [p for p in faltan if p in por_duro]
    w('Plugins del GASP.uproject que no salen en el cierre: %s' % ', '.join(
        sorted(p for p in en_gasp if en_gasp[p] and p not in necesita)))
    w('FALTAN en PruebaLumen.uproject (cierre completo): %s' % (', '.join(faltan) or 'ninguno'))
    w('FALTAN para el cierre duro: %s' % (', '.join(faltan_duros) or 'ninguno'))
    w('Otros paquetes fuera de /Game (no se copian; vienen con el motor o el plugin): %s' % ', '.join(otros)[:1500])

    # choques
    choques = sorted(p for p, v in info.items() if v['choca'])
    w('')
    w('=== Choques: rutas que ya existen en %s (%d)' % (content_tarsis, len(choques)))
    for p in choques:
        w('  %s [%s]%s' % (p, info[p]['clase'], '' if info[p]['duro'] else ' (solo blanda)'))
    carpetas_tarsis = sorted(os.listdir(content_tarsis))
    compartidas = sorted({p.split('/')[2] for p in info} & set(carpetas_tarsis))
    w('Carpetas raíz que ya existen en Tarsis y recibirían paquetes: %s' % ', '.join(compartidas))

    # lo que no queremos
    w('')
    w('=== Cosas que no queremos (duras = rompen si se cortan; solo blandas = se pueden dejar fuera)')

    def cadena(p, pad):
        c = [p]
        while c[-1] in pad and len(c) < 8:
            c.append(pad[c[-1]])
        return ' <- '.join(x.split('/')[-1] for x in c)

    for nombre, f in NO_QUEREMOS:
        hits = [p for p, v in info.items() if f(p, v['clase'])]
        if not hits:
            w('  %s: nada' % nombre)
            continue
        duros = [p for p in hits if info[p]['duro']]
        w('  %s: %d paquetes, %.1f MB (%d duros, %.1f MB)' % (nombre, len(hits), mb(sum(info[p]['bytes'] for p in hits)),
                                                           len(duros), mb(sum(info[p]['bytes'] for p in duros))))
        for p in sorted(duros)[:6]:
            w('    duro: %s   (cadena: %s)' % (p, cadena(p, padre_duro)))
        for p in sorted(set(hits) - set(duros))[:4]:
            w('    blando: %s   (cadena: %s)' % (p, cadena(p, padre)))
    grandes = sorted((v['bytes'], p) for p, v in info.items() if v['clase'].startswith('Texture') and v['bytes'] > 4 * 1048576)
    w('  texturas > 4 MB: %d, %.1f MB' % (len(grandes), mb(sum(b for b, _ in grandes))))
    for b, p in grandes[-10:][::-1]:
        w('    %.1f MB %s%s   (cadena: %s)' % (mb(b), p, '' if info[p]['duro'] else ' [solo blanda]',
                                             cadena(p, padre_duro if info[p]['duro'] else padre)))
    # qué arrastran las blandas desde las raíces (primer paso)
    w('')
    w('=== Referencias blandas directas de las raíces y de los componentes del personaje')
    for r in RAICES + ['/Game/Blueprints/AC_TraversalLogic', '/Game/Blueprints/SmartObjects/AC_SmartObjectAnimation',
                       '/Game/Blueprints/AC_VisualOverrideManager']:
        bl = set(deps(r, False, True)) - set(deps(r, True, False))
        bl = [x for x in bl if x.startswith('/Game/')]
        if bl:
            w('  %s (%d): %s' % (r.split('/')[-1], len(bl), ', '.join(sorted(x.split('/')[-1] for x in bl))[:600]))

    os.makedirs(DIR, exist_ok=True)
    open(TXT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    json.dump({'raices': RAICES, 'paquetes': info, 'faltan_plugins': faltan, 'faltan_plugins_duros': faltan_duros,
               'choques': choques},
              open(JSN, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    unreal.log('gasp_migrar seco: %d paquetes, %.1f MB, %d choques, faltan %s' % (len(info), mb(tot), len(choques), faltan))


# ======================================================================== copiar (sin Unreal)
def editor_tarsis_abierto():
    try:
        import subprocess
        out = subprocess.run(['powershell', '-NoProfile', '-Command',
                              "Get-CimInstance Win32_Process -Filter \"Name like 'UnrealEditor%'\" | "
                              "ForEach-Object { $_.CommandLine }"], capture_output=True, text=True).stdout
    except Exception:
        return True
    if 'PruebaLumen' in out:
        return True
    log = os.path.join(TARSIS, 'Saved', 'Logs', 'PruebaLumen.log')
    try:  # el editor de Tarsis tiene su log abierto en exclusiva
        os.rename(log, log)
    except OSError:
        return True
    return False


def copiar():
    d = json.load(open(JSN, encoding='utf-8'))
    blandas = os.environ.get('LH_GASP_BLANDAS') == '1'
    paquetes = {p: v for p, v in d['paquetes'].items() if v['duro'] or blandas}

    def distinto(rel):  # un fichero ya copiado antes por este script (mismo tamaño) no es un choque
        o, dst = os.path.join(GASP, 'Content', rel), os.path.join(TARSIS, 'Content', rel)
        return os.path.exists(dst) and os.path.getsize(dst) != os.path.getsize(o)

    choques = [p for p, v in paquetes.items()
               if any(distinto(r) for r in v['ficheros']) or
               (ficheros(os.path.join(TARSIS, 'Content'), p) and not any(
                   os.path.exists(os.path.join(TARSIS, 'Content', r)) for r in v['ficheros']))]
    if choques:
        sys.exit('NO se copia: %d choques (%s...)' % (len(choques), ', '.join(choques[:5])))
    if editor_tarsis_abierto():
        sys.exit('NO se copia: el editor de PruebaLumen está abierto')
    if not os.path.exists(UPROJECT + '.bak'):  # la copia buena es la de antes de la primera pasada
        shutil.copy2(UPROJECT, UPROJECT + '.bak')
    up, activos = plugins_uproject(UPROJECT)
    añadidos = [p for p in d['faltan_plugins' if blandas else 'faltan_plugins_duros'] if not activos.get(p)]
    for p in añadidos:
        up.setdefault('Plugins', []).append({'Name': p, 'Enabled': True})
    with open(UPROJECT, 'w', encoding='utf-8') as f:
        json.dump(up, f, indent='\t')
        f.write('\n')
    # las cvars DDCvar.* que lee el ABP (DataDrivenConsoleVariableSettings del GASP); sin ellas valen 0
    ini_t = os.path.join(TARSIS, 'Config', 'DefaultEngine.ini')
    ini_g = os.path.join(GASP, 'Config', 'DefaultEngine.ini')
    txt_t = open(ini_t, encoding='utf-8-sig').read()
    cvars = [l for l in open(ini_g, encoding='utf-8-sig').read().splitlines() if l.startswith('+CVarsArray=')]
    nuevas = [l for l in cvars if l not in txt_t]
    if nuevas:
        if not os.path.exists(ini_t + '.bak'):
            shutil.copy2(ini_t, ini_t + '.bak')
        with open(ini_t, 'a', encoding='utf-8') as f:
            f.write('\n[/Script/Engine.DataDrivenConsoleVariableSettings]\n' + '\n'.join(nuevas) + '\n')
    # gameplay tags del GASP (Foley.Event.*, SmartObject.*...): sin ellos las animaciones y el StateTree dan avisos
    tags_g = os.path.join(GASP, 'Config', 'DefaultGameplayTags.ini')
    tags_t = os.path.join(TARSIS, 'Config', 'DefaultGameplayTags.ini')
    n_tags = 0
    if not os.path.exists(tags_t):
        shutil.copy2(tags_g, tags_t)
        n_tags = sum(1 for l in open(tags_g, encoding='utf-8-sig') if l.startswith('+GameplayTag'))
    else:
        txt = open(tags_t, encoding='utf-8-sig').read()
        lineas = [l for l in open(tags_g, encoding='utf-8-sig').read().splitlines()
                  if l.startswith('+GameplayTag') and l not in txt]
        if lineas:
            if not os.path.exists(tags_t + '.bak'):
                shutil.copy2(tags_t, tags_t + '.bak')
            if '[/Script/GameplayTags.GameplayTagsSettings]' not in txt:
                lineas.insert(0, '[/Script/GameplayTags.GameplayTagsSettings]')
            with open(tags_t, 'a', encoding='utf-8') as f:
                f.write('\n' + '\n'.join(lineas) + '\n')
            n_tags = len(lineas)
    total = 0
    for p, v in paquetes.items():
        for rel in v['ficheros']:
            o = os.path.join(GASP, 'Content', rel)
            dst = os.path.join(TARSIS, 'Content', rel)
            if os.path.exists(dst):
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(o, dst)
            total += os.path.getsize(o)
    print('copiados %d paquetes, %.1f MB nuevos; plugins añadidos: %s; %d cvars DDCvar y %d gameplay tags añadidos; '
          'copias en %s.bak%s' % (len(paquetes), mb(total), ', '.join(añadidos) or 'ninguno', len(nuevas), n_tags,
                                  UPROJECT, ' y DefaultEngine.ini.bak' if nuevas else ''))


# ======================================================================== comprobar (dentro de Tarsis)
def comprobar():
    import unreal
    L = []
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for p in ('/Game/Blueprints/SandboxCharacter_CMC_ABP', '/Game/Blueprints/SandboxCharacter_CMC',
              '/Game/Blueprints/RetargetedCharacters/ABP_GenericRetarget'):
        bp = unreal.load_asset(p)
        if not bp:
            L.append('%s: NO carga' % p)
            continue
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            st = bp.get_editor_property('status') if hasattr(bp, 'get_editor_property') else None
        except Exception as e:
            st = 'excepción %s' % e
        L.append('%s: carga, compilado, estado %s' % (p, st))
    todo = reg.get_assets_by_path('/Game', recursive=True)
    psd = [a for a in todo if str(a.asset_class_path.asset_name) == 'PoseSearchDatabase']
    L.append('Bases de Pose Search en el registro: %d' % len(psd))
    salida = os.path.join(DIR, 'gasp_migrar_comprobar.txt')
    open(salida, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    unreal.log('gasp_migrar comprobar: ' + ' | '.join(L))


{'seco': seco, 'copiar': copiar, 'comprobar': comprobar}[MODO]()
