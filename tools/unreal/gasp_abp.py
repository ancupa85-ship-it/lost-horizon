"""Cómo se conecta el ABP del Game Animation Sample (GASP) a su personaje, para enchufarlo a Cuttlas y a ATarsisGuard.

Se lanza en el proyecto del GASP sin abrir ventana:
    D:\\ue_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe "D:\\GASP\\GameAnimationSample.uproject" -run=pythonscript -script="<repo>\\tools\\unreal\\gasp_abp.py" -unattended -nosplash -nullrhi
Escribe D:\\LostHorizon\\gasp_abp.txt (o la ruta de LH_GASP_ABP_SALIDA) con:
  1. SandboxCharacter_CMC_ABP y SandboxCharacter_CMC: interfaces, variables, funciones, componentes y de dónde lee
     el ABP los datos del personaje.
  2. La cadena de Choosers -> bases de Pose Search que corre por defecto con el personaje CMC, con cuántas animaciones
     distintas suman y cuánto ocupan en disco.
  3. ABP_GenericRetarget: retarget en tiempo real, IK Retargeters y esqueletos fuente/destino.
  4. Secuencias de agacharse, girar en el sitio y apuntar/armas.

Python no puede leer los nodos de los grafos (EdGraph.Nodes está protegida), así que el contenido de los grafos se
saca de la etiqueta FiBData del registro de assets: es el índice de «Buscar en Blueprints», con los textos de todos los
nodos, pines y comentarios, guardados con cada carácter desplazado +1.
"""
import os
import re
import unreal

SALIDA = os.environ.get('LH_GASP_ABP_SALIDA') or r'D:\LostHorizon\gasp_abp.txt'

ABP = '/Game/Blueprints/SandboxCharacter_CMC_ABP'
PJ = '/Game/Blueprints/SandboxCharacter_CMC'
BPI_PAWN = '/Game/Blueprints/BPI_SandboxCharacter_Pawn'
BPI_ABP = '/Game/Blueprints/BPI_SandboxCharacter_ABP'
RETARGET = '/Game/Blueprints/RetargetedCharacters/ABP_GenericRetarget'
CHT_MM = '/Game/Characters/UEFN_Mannequin/Animations/MotionMatchingData/CHT_PoseSearchDatabases'
CHT_SM = '/Game/Characters/UEFN_Mannequin/Animations/ExperimentalStateMachineData/CHT_CMCCharacterAnimations'
STRUCTS = ['/Game/Blueprints/Data/S_CharacterPropertiesForAnimation', '/Game/Blueprints/Data/S_PlayerInputState']

reg = unreal.AssetRegistryHelpers.get_asset_registry()
BEL = unreal.BlueprintEditorLibrary
CONTENT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
L = []


def w(s=''):
    L.append(s)


def corto(s):
    """/Script/CoreUObject.Class'/Script/Engine.Character' -> /Script/Engine.Character"""
    m = re.search(r"'([^']+)'", s or '')
    return m.group(1) if m else (s or '')


def datos(paquete):
    ads = reg.get_assets_by_package_name(paquete)
    return ads[0] if ads else None


def clase_de(paquete):
    a = datos(paquete)
    return str(a.asset_class_path.asset_name) if a else '?'


def etiqueta(paquete, nombre):
    a = datos(paquete)
    if not a:
        return ''
    try:
        return str(a.get_tag_value(nombre) or '')
    except Exception:
        return ''


def deps(paquete, blandas=True):
    try:
        o = unreal.AssetRegistryDependencyOptions(include_soft_package_references=blandas,
                                                  include_hard_package_references=True)
        return [str(x) for x in reg.get_dependencies(paquete, o) or []]
    except Exception:
        return []


def referencias(paquete):
    try:
        o = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
                                                  include_hard_package_references=True)
        return [str(x) for x in reg.get_referencers(paquete, o) or []]
    except Exception:
        return []


def archivo(paquete):
    if not paquete.startswith('/Game/'):
        return None
    return os.path.join(CONTENT, paquete[len('/Game/'):].replace('/', os.sep) + '.uasset')


def bytes_paquete(paquete):
    f = archivo(paquete)
    t = 0
    for ext in ('', ):
        if f and os.path.exists(f):
            t += os.path.getsize(f)
            uexp = f[:-len('.uasset')] + '.uexp'
            if os.path.exists(uexp):
                t += os.path.getsize(uexp)
    return t


def fib(paquete):
    """Textos del índice de Buscar en Blueprints (FiBData), descifrados y sin repetir."""
    s = etiqueta(paquete, 'FiBData')
    d = ''.join(chr(ord(c) - 1) if ord(c) > 32 else c for c in s)
    return list(dict.fromkeys(m.group(0).strip() for m in re.finditer(r'[\x20-\x7e]{3,}', d)))


def filtra(textos, patron, maximo=60, largo=110):
    r = [x for x in textos if re.search(patron, x) and len(x) <= largo]
    return r[:maximo], len(r)


def interfaces(paquete):
    """ImplementedInterfaces = ((Interface="...BPI_X_C'",Graphs=("...:Funcion'",...)),...)"""
    t = etiqueta(paquete, 'ImplementedInterfaces')
    r = []
    for bloque in re.findall(r'\(Interface=(.*?)\)\)', t):
        nombre = re.search(r"'([^']+)'", bloque)
        funcs = re.findall(r":([A-Za-z0-9_]+)'", bloque)
        r.append((nombre.group(1) if nombre else bloque[:80], funcs))
    return r


def tipo_pin(t):
    """FEdGraphPinType tiene los campos protegidos: se lee su texto exportado (o el JSON schema de 5.8)."""
    txt = ''
    try:
        txt = t.export_text()
    except Exception:
        pass
    if txt:
        cat = re.search(r'PinCategory="?([^",)]+)', txt)
        sub = re.search(r"PinSubCategoryObject=[^']*'([^']+)'", txt)
        cont = re.search(r'ContainerType=(\w+)', txt)
        s = (cat.group(1) if cat else '?') + ('<%s>' % sub.group(1).split('.')[-1] if sub else '')
        if cont and cont.group(1) not in ('None',):
            s += '[%s]' % cont.group(1)
        return s
    try:
        return re.sub(r'\s+', ' ', str(BEL.pin_type_to_json_schema(t)))[:80]
    except Exception:
        return '?'


def variables(bp):
    """Variables propias del blueprint (sin las heredadas de la clase C++), como 'nombre:tipo'."""
    r = []
    try:
        for n in BEL.list_member_variable_names(bp):
            n = str(n)
            if n.startswith('/Script/'):
                continue
            try:
                r.append('%s:%s' % (n, tipo_pin(BEL.get_member_variable_type(bp, n))))
            except Exception:
                r.append(n)
    except Exception as e:
        r.append('(no se pudo listar: %s)' % e)
    return r


def en_lineas(titulo, items, ancho=150):
    w('%s (%d):' % (titulo, len(items)))
    linea = ' '
    for x in items:
        if len(linea) + len(x) + 2 > ancho:
            w(linea.rstrip(', '))
            linea = ' '
        linea += ' ' + x + ','
    if linea.strip():
        w(linea.rstrip(', '))


def grafos(bp):
    for f in ('list_graph_names', 'list_functions'):
        try:
            v = getattr(BEL, f)(bp)
            nombres = [str(x if isinstance(x, str) else getattr(x, 'get_name', lambda: x)()) for x in v]
            # quita estados/transiciones repetidos de las máquinas de estados
            return [x for x in dict.fromkeys(nombres) if x not in ('Transition',) and not x.startswith('AnimationTransitionGraph')], f
        except Exception:
            continue
    return [], None


def t3d(paquete):
    """Exporta un asset a texto T3D (vale para assets que no son blueprints, como ChooserTable)."""
    f = os.path.join(os.path.dirname(SALIDA), 'gasp_t3d', paquete.split('/')[-1] + '.t3d')
    os.makedirs(os.path.dirname(f), exist_ok=True)
    try:
        tarea = unreal.AssetExportTask()
        tarea.set_editor_property('object', unreal.load_asset(paquete))
        tarea.set_editor_property('filename', f)
        tarea.set_editor_property('automated', True)
        tarea.set_editor_property('prompt', False)
        tarea.set_editor_property('replace_identical', True)
        if unreal.Exporter.run_asset_export_task(tarea) and os.path.exists(f):
            return open(f, encoding='utf-8', errors='ignore').read()
    except Exception:
        pass
    return ''


def componentes(bp):
    r = []
    try:
        sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        for h in sub.k2_gather_subobject_data_for_blueprint(bp):
            d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
            o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
            if o:
                r.append('%s (%s)' % (o.get_name().replace('_GEN_VARIABLE', ''), o.get_class().get_name()))
    except Exception as e:
        r.append('(no se pudo listar: %s)' % e)
    return r


def campos_struct(paquete):
    f = archivo(paquete)
    if not f or not os.path.exists(f):
        return []
    t = open(f, 'rb').read().decode('latin-1')
    return list(dict.fromkeys(re.sub(r'_\d+_[0-9A-F]{32}$', '', m) for m in
                              re.findall(r'[A-Za-z][A-Za-z0-9_]*_\d+_[0-9A-F]{32}', t)))


def lista(titulo, items, sangria='  '):
    w('%s (%d):' % (titulo, len(items)))
    for x in items:
        w(sangria + '- ' + str(x))


# ---------------------------------------------------------------- 1. ABP y personaje
w('GASP - cómo conectar SandboxCharacter_CMC_ABP a un ACharacter propio (gasp_abp.py)')
w('Proyecto: %s' % unreal.Paths.get_project_file_path())
w('')
w('=== 1. %s' % ABP)
abp = unreal.load_asset(ABP)
w('Padre: %s   Esqueleto: %s' % (corto(etiqueta(ABP, 'ParentClass')), corto(etiqueta(ABP, 'TargetSkeleton'))))
for nombre, funcs in interfaces(ABP):
    w('Implementa %s: %s' % (nombre, ', '.join(funcs)))
fa = fib(ABP)
w('')
w('De dónde saca los datos del personaje (textos de los nodos, FiBData):')
for tit, pat in [
        ('Dueño', r'^(TryGetPawnOwner|Get Owning Actor|GetOwningActor|Get Owning Component|GetOwningComponent)$'),
        ('Casts', r'^Cast To |K2Node_DynamicCast_As'),
        ('Interfaces que llama', r'^/Game/.*BPI_|^Get_PropertiesFor|^Get_MMIResult|^Set_IsPlayingRootMotion'),
        ('Movimiento / trayectoria', r'(Character Movement|CharacterMovement|Movement Component|Pose Search Generate Trajectory|PoseSearchGenerate|HandleTrajectoryWorldCollisions|Get Velocity$|Get Current Acceleration)'),
        ('Lecturas de Character Properties', r'^Character Properties\.'),
        ('Console variables', r'^(DDCvar|DDCVar|a\.animnode)\.'),
        ('Nodos del AnimGraph', r'^(Motion Matching|Blend Stack|Offset Root Bone|Orientation Warping|Stride Warping|Steering|Foot Placement|Leg IK|Aim Offset|Pose History|State Machine Blend Stack|Evaluate Chooser: .*|CHT_\w+)$')]:
    r, n = filtra(fa, pat)
    w('  %s (%d): %s' % (tit, n, ' | '.join(r)))
w('')
en_lineas('Variables del ABP (nombre:tipo)', variables(abp))
g, via = grafos(abp)
en_lineas('Grafos/funciones/estados del ABP (%s)' % via, g)
w('Dependencias directas (assets /Game):')
for d in deps(ABP):
    if d.startswith('/Game/'):
        w('  - %s [%s]' % (d, clase_de(d)))

w('')
w('=== %s' % PJ)
pj = unreal.load_asset(PJ)
w('Padre: %s' % corto(etiqueta(PJ, 'ParentClass')))
for nombre, funcs in interfaces(PJ):
    w('Implementa %s: %s' % (nombre, ', '.join(funcs)))
en_lineas('Componentes', [c for c in componentes(pj) if not c.startswith('Default__')])
en_lineas('Variables (nombre:tipo)', variables(pj))
g, via = grafos(pj)
en_lineas('Grafos/funciones (%s)' % via, g)
fp = fib(PJ)
for tit, pat in [
        ('Lecturas de CharacterMovement', r'(Character Movement|CharacterMovement|Get Velocity|Get Current Acceleration|Max Acceleration|Braking|Is Falling|Is Moving On Ground|Movement Mode|Max Walk Speed|Get Last Update Velocity|Is Crouching|Ground)'),
        ('Motion Warping / Trajectory / Chooser', r'(Motion ?Warp|Trajectory|Chooser|CHT_|Pose ?Search)'),
        ('Funciones de la interfaz', r'^(Get_|Set_)\w+$')]:
    r, n = filtra(fp, pat)
    w('  %s (%d): %s' % (tit, n, ' | '.join(r)))
for p in (BPI_PAWN, BPI_ABP):
    funcs = re.findall(r'(?:Get|Set)_[A-Za-z]+', open(archivo(p), 'rb').read().decode('latin-1'))
    w('Funciones de %s: %s' % (p.split('/')[-1], ', '.join(dict.fromkeys(funcs))))
for s in STRUCTS:
    w('Campos de %s: %s' % (s.split('/')[-1], ', '.join(campos_struct(s))))
w('Quién usa el ABP (referencers): %s' % ', '.join(referencias(ABP)))

# ---------------------------------------------------------------- 2. cadena por defecto
w('')
w('=== 2. Choosers y bases de Pose Search por defecto')
ini = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_config_dir()), 'DefaultEngine.ini')
cv = {}
if os.path.exists(ini):
    for linea in open(ini, encoding='utf-8', errors='ignore'):
        m = re.search(r'Type=(\w+),Name="([^"]+)".*DefaultValueFloat=([^,]+),DefaultValueInt=([^,]+),DefaultValueBool=(\w+)', linea)
        if m:
            cv[m.group(2)] = m
for k in ('DDCVar.ExperimentalStateMachine.Enable', 'DDCvar.MMDatabaseLOD', 'DDCvar.LocomotionSetupCMC', 'DDCVar.DefaultAnimSet'):
    m = cv.get(k)
    w('  cvar %s: %s' % (k, ('%s float=%s int=%s bool=%s' % (m.group(1), m.group(3), m.group(4), m.group(5)))
                          if m else 'no está en DefaultEngine.ini'))

ANIM = ('AnimSequence', 'BlendSpace', 'BlendSpace1D', 'AnimComposite', 'AnimMontage', 'AimOffsetBlendSpace')


def arbol(raiz, nivel=0, visto=None, acum=None):
    """Recorre Chooser -> (Chooser anidado | PoseSearchDatabase) y junta las animaciones de cada base."""
    visto = visto if visto is not None else set()
    acum = acum if acum is not None else {'psd': [], 'anims': set()}
    if raiz in visto:
        return acum
    visto.add(raiz)
    c = clase_de(raiz)
    if c == 'PoseSearchDatabase':
        anims = set()
        try:
            db = unreal.load_asset(raiz)
            for i in range(db.get_num_animation_assets()):
                o = db.get_animation_asset(i)
                if o:
                    anims.add(o.get_outermost().get_name())
        except Exception:
            pass
        if not anims:
            anims = {d for d in deps(raiz, False) if clase_de(d) in ANIM}
        # las blendspaces cuentan con sus secuencias
        for a in list(anims):
            if clase_de(a) != 'AnimSequence':
                anims |= {d for d in deps(a, False) if clase_de(d) == 'AnimSequence'}
        seqs = {a for a in anims if clase_de(a) == 'AnimSequence'}
        acum['psd'].append((nivel, raiz, len(anims), len(seqs)))
        acum['anims'] |= seqs
        w('  ' + '  ' * nivel + '%s [PSD, %d assets, %d secuencias]' % (raiz.split('/')[-1], len(anims), len(seqs)))
        return acum
    hijos = [d for d in deps(raiz) if d.startswith('/Game/')]
    directas = {d for d in hijos if clase_de(d) in ANIM}
    for a in list(directas):
        if clase_de(a) != 'AnimSequence':
            directas |= {d for d in deps(a, False) if clase_de(d) == 'AnimSequence'}
    seqs = {a for a in directas if clase_de(a) == 'AnimSequence'}
    acum['anims'] |= seqs
    w('  ' + '  ' * nivel + '%s [%s]%s' % (raiz, c, (' (%d animaciones directas, %d secuencias)' % (len(directas), len(seqs))) if directas else ''))
    for d in hijos:
        if clase_de(d) in ('ChooserTable', 'PoseSearchDatabase'):
            if d in visto:
                w('  ' + '  ' * (nivel + 1) + '%s (ya listado arriba)' % d.split('/')[-1])
            arbol(d, nivel + 1, visto, acum)
    return acum


def filas_lod(paquete):
    """Rangos de la columna MMDatabaseLOD y resultado de cada fila, leídos del T3D del chooser."""
    txt = t3d(paquete)
    if not txt:
        return 'no se pudo exportar a T3D'
    rangos = re.findall(r'Min=([-\d.]+),Max=([-\d.]+)', txt)
    res = re.findall(r'(CHT_PoseSearchDatabases_\w+)', txt)
    res = list(dict.fromkeys(res))
    return 'filas (min..max -> resultado, en orden del T3D): ' + ' | '.join(
        '%s..%s -> %s' % (a, b, r) for (a, b), r in zip(rangos, res)) + ('   [rangos %d, resultados %d]' % (len(rangos), len(res)))


def resumen(acum, titulo):
    mb = sum(bytes_paquete(a) for a in acum['anims']) / 1048576.0
    w('  => %s: %d bases de Pose Search, %d secuencias distintas, %.1f MB en disco (.uasset de esas secuencias)'
      % (titulo, len(acum['psd']), len(acum['anims']), mb))
    return mb


w('Motion Matching (ruta por defecto, ExperimentalStateMachine=0): %s' % CHT_MM)
w('  El chooser raíz elige el subchooser con una columna de rango sobre la cvar MMDatabaseLOD.')
w('  ' + filas_lod(CHT_MM))
mm = arbol(CHT_MM)
resumen(mm, 'Total de los tres niveles de LOD')
w('  Por subchooser (cada uno con sus choosers anidados):')
for sub in deps(CHT_MM):
    if clase_de(sub) == 'ChooserTable':
        a = {'psd': [], 'anims': set()}
        n0 = len(L)
        arbol(sub, 0, set(), a)
        anidados = [x.strip().split(' ')[0].split('/')[-1] for x in L[n0 + 1:] if '[ChooserTable]' in x]
        del L[n0:]  # el árbol ya se listó arriba
        resumen(a, sub.split('/')[-1] + (' (+ anidados: %s)' % ', '.join(anidados) if anidados else ''))
w('')
w('State machine experimental (DDCVar.ExperimentalStateMachine.Enable=1): %s' % CHT_SM)
sm = arbol(CHT_SM)
resumen(sm, 'State machine experimental')
otros = [d for d in deps(ABP) if clase_de(d) in ('ChooserTable', 'PoseSearchDatabase')]
w('Choosers/bases que el ABP referencia directamente: %s' % ', '.join(otros))

# ---------------------------------------------------------------- 3. retarget
w('')
w('=== 3. %s' % RETARGET)
w('Padre: %s   Esqueleto del ABP: %s' % (corto(etiqueta(RETARGET, 'ParentClass')), corto(etiqueta(RETARGET, 'TargetSkeleton')) or '(ninguno: ABP plantilla/genérico)'))
rt = unreal.load_asset(RETARGET)
lista('Variables', variables(rt))
fr = fib(RETARGET)
r, n = filtra(fr, r'(Retarget|IK ?Rig|Source|Copy Pose|Leader|Mesh)', 80, 140)
w('Textos de nodos sobre retarget (%d): %s' % (n, ' | '.join(r)))
w('Quién lo usa (referencers): %s' % ', '.join(referencias(RETARGET)))
w('IK Retargeters que referencia:')


def malla_de_rig(rig):
    for n in ('preview_skeletal_mesh', 'PreviewSkeletalMesh'):
        try:
            m = rig.get_editor_property(n)
            if m:
                return m
        except Exception:
            pass
    return None


for d in deps(RETARGET):
    if clase_de(d) != 'IKRetargeter':
        continue
    try:
        rtg = unreal.load_asset(d)
        c = unreal.IKRetargeterController.get_controller(rtg)
        partes = []
        for lado in ('SOURCE', 'TARGET'):
            rig = c.get_ik_rig(getattr(unreal.RetargetSourceOrTarget, lado))
            m = malla_de_rig(rig) if rig else None
            esq = m.get_editor_property('skeleton') if m else None
            partes.append('%s: rig %s, malla %s, esqueleto %s' % (
                lado.lower(), rig.get_name() if rig else None, m.get_name() if m else None,
                esq.get_path_name() if esq else None))
        try:
            ops = c.get_num_retarget_ops()
            partes.append('%d ops' % ops)
        except Exception:
            pass
        w('  - %s: %s' % (d, '; '.join(partes)))
    except Exception as e:
        w('  - %s: (error %s)' % (d, e))

# ---------------------------------------------------------------- 4. secuencias útiles
w('')
w('=== 4. Secuencias de agacharse, girar en el sitio y apuntar/armas')
seqs = [a for a in reg.get_assets_by_path('/Game', recursive=True) if str(a.asset_class_path.asset_name) == 'AnimSequence']
for tit, pat in [('Agacharse (Crouch)', r'crouch'),
                 ('Girar en el sitio (Turn / TurnInPlace / Spin)', r'turn|spin|tip_|_tip'),
                 ('Apuntar / armas (Aim, AO_, Pistol, Rifle, Gun, Weapon, Shoot, Fire, ADS)', r'aim|_ao_|^ao_|pistol|rifle|gun|weapon|shoot|fire|_ads|ads_')]:
    hits = [a for a in seqs if re.search(pat, str(a.asset_name), re.I)]
    if tit.startswith('Agacharse'):
        hits = [a for a in seqs if re.search(pat, str(a.asset_name) + str(a.package_path), re.I)]
    w('%s: %d' % (tit, len(hits)))
    por = {}
    for a in hits:
        por.setdefault(str(a.package_path), []).append(str(a.asset_name))
    for carpeta in sorted(por):
        en_lineas('  ' + carpeta, sorted(por[carpeta]), 170)

os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
with open(SALIDA, 'w', encoding='utf-8') as f:
    f.write('\n'.join(L) + '\n')
unreal.log('GASP ABP: escrito %s (%d líneas)' % (SALIDA, len(L)))
