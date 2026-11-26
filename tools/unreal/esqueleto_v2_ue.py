"""Tanda M: monta en el editor las personas con el esqueleto recolocado (assets/unreal/personas/<p>_v2.glb, de
tools/vestuario/esqueleto_v2.py) sin cambiar ninguna referencia del nivel ni del código.

Para cada persona se reimporta su .glb _v2 en la MISMA carpeta y con los mismos nombres que la de antes
(/Game/Tarsis/Personas/<p>_<huella>), así que el guardia, su RTG_UEFN_<p> y la copia RifleRef siguen apuntando a la misma
malla. Después se rehacen las poses de fusil retargeteadas (MM_Rifle_Idle_Hipfire_<p>, MM_Rifle_Idle_ADS_<p>): llevan la
traslación de cada hueso y, con las de antes, los brazos volverían a su sitio viejo al empuñar el fusil.

Volver a la v1 de una persona: LH_ESQ_VARIANTE=v1 LH_ESQ_SOLO=ibarra (reimporta su .glb de antes del mismo modo).
Escribe D:\\LostHorizon\\capturas-tandaM\\esqueleto_ue.txt."""
import builtins
import os
import unreal

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARPETA = os.path.join(ROOT, 'assets', 'unreal', 'personas')
PERSONAS = ['centinela', 'ibarra', 'moya', 'peris', 'ramos', 'vega', 'roig', 'cuttlas']
# por variable de entorno o, desde la ejecucion remota, builtins._esq_variante / builtins._esq_solo
VARIANTE = getattr(builtins, '_esq_variante', None) or os.environ.get('LH_ESQ_VARIANTE', 'v2')
SOLO = [x for x in (getattr(builtins, '_esq_solo', None) or os.environ.get('LH_ESQ_SOLO', '')).split(',') if x]
SALIDA = r'D:\LostHorizon\capturas-tandaM\esqueleto_ue.txt'
EAL = unreal.EditorAssetLibrary
reg = unreal.AssetRegistryHelpers.get_asset_registry()
L = []


def w(*a):
    s = ' '.join(str(x) for x in a)
    L.append(s)
    unreal.log('[EsqueletoV2] ' + s)


def carpeta_de(p):
    """La carpeta /Game/Tarsis/Personas/<p>_<huella> que usa ahora el juego (la malla de vista previa del RTG)."""
    rtg = unreal.load_asset('/Game/Tarsis/Anim/RTG_UEFN_%s' % p)
    if rtg:
        try:
            m = unreal.IKRetargeterController.get_controller(rtg).get_preview_mesh(unreal.RetargetSourceOrTarget.TARGET)
            if m:
                return m.get_path_name().rsplit('/', 1)[0], m
        except Exception as ex:
            w(p, 'sin malla de vista previa en el RTG:', ex)
    return None, None


def reimportar(p, carpeta, glb):
    pipe = unreal.InterchangeGenericAssetsPipeline()
    pipe.get_editor_property('mesh_pipeline').set_editor_property(
        'combine_skeletal_meshes_behavior', unreal.InterchangeCombineSkeletalMeshesBehavior.BY_SKELETON)
    params = unreal.ImportAssetParameters()
    params.set_editor_property('is_automated', True)
    params.set_editor_property('replace_existing', True)
    ov = params.get_editor_property('override_pipelines')
    ov.append(unreal.SoftObjectPath(pipe.get_path_name()))
    params.set_editor_property('override_pipelines', ov)
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    res = mgr.import_asset(carpeta, unreal.InterchangeManager.create_source_data(glb), params)
    n = 0
    for r in res or []:
        a = EAL.load_asset(str(r).split("'")[1] if "'" in str(r) else str(r))
        if a:
            EAL.save_loaded_asset(a, False)
            n += 1
    return n


def fusil(p, malla):
    uefn = unreal.load_asset('/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin')
    rtg = unreal.load_asset('/Game/Tarsis/Anim/RTG_UEFN_%s' % p)
    fuentes = [unreal.load_asset('/Game/Tarsis/Armas/Anims/%s' % n) for n in ('MM_Rifle_Idle_Hipfire', 'MM_Rifle_Idle_ADS')]
    fuentes = [f for f in fuentes if f]
    if not (uefn and rtg and fuentes):
        w(p, 'fusil: falta algo', bool(uefn), bool(rtg), len(fuentes))
        return
    for a in fuentes:
        dest = '/Game/Tarsis/Armas/Anims/%s_%s' % (a.get_name(), p)
        if EAL.does_asset_exist(dest):
            EAL.delete_asset(dest)
    r = unreal.IKRetargetBatchOperation.duplicate_and_retarget([EAL.find_asset_data(x.get_path_name()) for x in fuentes], uefn, malla, rtg,
                                                                '', '', '', '_' + p, '/Game/Tarsis/Armas/Anims', False, False, True)
    for x in r:
        EAL.save_asset(str(x.package_name), False)
    w(p, 'fusil retargeteado:', [str(x.asset_name) for x in r])


def main():
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    w('variante', VARIANTE)
    for p in PERSONAS:
        if SOLO and p not in SOLO:
            continue
        glb = os.path.join(CARPETA, p + ('_v2' if VARIANTE == 'v2' else '') + '.glb')
        if not os.path.exists(glb):
            w(p, 'falta', glb)
            continue
        carpeta, antes = carpeta_de(p)
        if not carpeta:
            w(p, 'sin carpeta en uso')
            continue
        nombre = antes.get_name()
        n = reimportar(p, carpeta, glb)
        malla = unreal.load_asset('%s/%s' % (carpeta, nombre))
        w(p, 'reimportada en', carpeta, '(%d assets)' % n, 'malla', malla.get_path_name() if malla else None,
          'materiales', len(malla.get_editor_property('materials')) if malla else 0)
        if malla:
            try:
                fusil(p, malla)
            except Exception as ex:
                w(p, 'fusil: fallo', repr(ex))
    with open(SALIDA, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


main()
