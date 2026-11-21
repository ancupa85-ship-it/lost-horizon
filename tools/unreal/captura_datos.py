"""Tanda A, novena: datos de las parejas del GASP para la detencion (empujon parado y derribo parado), en el editor de
Tarsis. Para cada pareja y direccion (F, B, L, R): duracion de la parte del guardia (_A) y de Cuttlas (_V), la raiz de
cada una al empezar (las dos estan grabadas en el mismo espacio: la de _A respecto a la de _V dice donde se pone el
guardia), cuando se cae Cuttlas (aviso TriggerRagdoll del montaje de _V), cuando golpea el guardia (FoleyEvent_Punch y
la sacudida de camara del montaje de _A) y donde acaba la raiz de _A.
Los montajes del GASP se leen de una copia temporal en /Game/_tmp_gasp_montajes (sus avisos son Blueprints que Tarsis no
tiene: solo se leen los tiempos y los nombres) que este script borra al acabar.
Escribe D:\\LostHorizon\\captura_datos.txt y la tabla C++ en unreal/Source/Tarsis/TarsisCapturaDatos.inl."""
import os
import unreal

unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(
    ['/Game/_tmp_gasp_montajes', '/Game/Characters/UEFN_Mannequin/Animations/Interactions'], True)

AL = unreal.AnimationLibrary
SEQ = {'shove': '/Game/Characters/UEFN_Mannequin/Animations/Interactions/Shoves/M_relaxed_ragdoll_shove_stand_%s_%s',
       'takedown': '/Game/Characters/UEFN_Mannequin/Animations/Interactions/Takedowns/M_relaxed_takedown_stand_%s_%s_'}
MON = {'shove': '/Game/_tmp_gasp_montajes/AM_M_relaxed_ragdoll_shove_stand_%s_%s',
       'takedown': '/Game/_tmp_gasp_montajes/AM_M_relaxed_takedown_stand_%s_%s'}
HERE = os.path.dirname(os.path.abspath(__file__))
INL = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'unreal', 'Source', 'Tarsis', 'TarsisCapturaDatos.inl')
L = []


def raiz(seq, t):
    tr = AL.get_bone_pose_for_time(seq, 'root', t, False)
    return tr


def avisos(m):
    """(nombre del aviso, segundo) del montaje; los Blueprints de los avisos no estan, pero el nombre si"""
    if not m:
        return []
    return [(str(e.notify_name), round(AL.get_anim_notify_event_trigger_time(e), 3)) for e in AL.get_animation_notify_events(m)]


filas = []
for tipo in ('shove', 'takedown'):
    for d in ('F', 'B', 'L', 'R'):
        a = unreal.load_asset(SEQ[tipo] % (d, 'A'))
        v = unreal.load_asset(SEQ[tipo] % (d, 'V'))
        ma = unreal.load_asset(MON[tipo] % (d, 'A'))
        mv = unreal.load_asset(MON[tipo] % (d, 'V'))
        if not a or not v:
            L.append('%s %s: FALTA %s %s' % (tipo, d, a, v))
            continue
        ra, rv = raiz(a, 0.0), raiz(v, 0.0)
        rel = ra.make_relative(rv) if hasattr(ra, 'make_relative') else None
        la, lv = a.get_play_length(), v.get_play_length()
        ra_fin = raiz(a, la)
        av_v, av_a = avisos(mv), avisos(ma)
        caida = min([t for n, t in av_v if 'Ragdoll' in n] or [lv * 0.8])
        golpe = min([t for n, t in av_a if 'Punch' in n or 'Shake' in n] or [caida])
        fin_a = min([t for n, t in av_a if 'BlendOut' in n] or [la])
        L.append('%s %s: A %.2f s V %.2f s root_motion A=%s V=%s' % (tipo, d, la, lv, a.get_editor_property('enable_root_motion'), v.get_editor_property('enable_root_motion')))
        L.append('   raiz A0 %s rot %s | V0 %s rot %s' % (ra.translation, ra.rotation.rotator(), rv.translation, rv.rotation.rotator()))
        L.append('   A respecto a V: %s yaw %.1f | raiz A al final %s' % (rel.translation if rel else '?', rel.rotation.rotator().yaw if rel else 0, ra_fin.translation))
        L.append('   avisos V %s' % av_v)
        L.append('   avisos A %s' % av_a)
        L.append('   caida %.3f golpe %.3f fin A %.3f' % (caida, golpe, fin_a))
        filas.append((tipo, d, la, lv, ra, rv, caida, golpe, fin_a))

# tabla C++
with open(INL, 'w', encoding='utf-8', newline='\n') as f:
    f.write('// Generado por tools/unreal/captura_datos.py: parejas del GASP para la detencion. No editar a mano.\n')
    f.write('// Tipo, direccion, duracion A y V, raiz A y V al empezar (espacio comun de la grabacion: x, y, z, yaw),\n')
    f.write('// segundo en que cae Cuttlas (TriggerRagdoll), en que golpea el guardia, y en que el guardia ya puede soltarse.\n')
    for tipo, d, la, lv, ra, rv, caida, golpe, fin_a in filas:
        ta, tv = ra.translation, rv.translation
        f.write('{ TEXT("%s"), TEXT("%s"), %.4ff, %.4ff, FVector(%.3ff, %.3ff, %.3ff), %.3ff, FVector(%.3ff, %.3ff, %.3ff), %.3ff, %.4ff, %.4ff, %.4ff },\n' % (
            tipo, d, la, lv, ta.x, ta.y, ta.z, ra.rotation.rotator().yaw, tv.x, tv.y, tv.z, rv.rotation.rotator().yaw, caida, golpe, fin_a))
open(r'D:\LostHorizon\captura_datos.txt', 'w', encoding='utf-8').write('\n'.join(L))
# la copia temporal de los montajes fuera
unreal.EditorAssetLibrary.delete_directory('/Game/_tmp_gasp_montajes')
