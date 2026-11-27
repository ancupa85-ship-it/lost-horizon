"""Tanda P: piezas propias del cuerpo a cuerpo, hechas en Blender a partir de animaciones de base del maniqui.

No son de Lyra tal cual: cada pieza se rehace con su propio ritmo (anticipacion, golpe, seguimiento y vuelta) y con las
poses clave exageradas, que es lo que las charlas de combate (Cooper, Sekiro, God of War) dicen que vende el golpe:
- el tiempo se remapea por tramos (TRAMOS: segundo nuevo -> segundo de la base), muestreando la base y clavando claves;
- en las ventanas de EXAGERAR, la rotacion de los huesos se aleja de la pose de reposo por un factor (mapa exponencial);
- las piezas en pareja salen en el mismo espacio: la raiz de Cuttlas en el origen y los dos con el mismo sentido.

Uso (Blender sin ventana):
  blender.exe -b --factory-startup --python tools/blender/cqc_anims.py -- <pieza> <fbx_base> <fbx_salida>
Piezas: culatazo, punetazo, contra, agarre_guardia, agarre_cuttlas (ver PIEZAS). Imprime los segundos clave para el C++.
"""
import json, math, os, sys
import bpy
from mathutils import Matrix, Quaternion, Vector

FPS = 60

# pieza -> (tramos [(t_nuevo, t_base), ...], exagerar [(t0, t1, factor, huesos)], claves que se publican)
BRAZOS = ['clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r', 'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l']
TRONCO = ['spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'neck_01']
PIEZAS = {
    # el culatazo del guardia: sube la culata despacio y mas alta (0 -> 0,45 s), latigazo al contacto (0,45 -> 0,52),
    # seguimiento largo y vuelta. En la base: arriba 0,27 s, contacto 0,34 s
    'culatazo': ([(0.0, 0.0), (0.45, 0.27), (0.52, 0.34), (0.80, 0.55), (1.30, 1.17)],
                 [(0.25, 0.50, 1.35, BRAZOS + TRONCO), (0.52, 0.75, 1.25, TRONCO)],
                 {'arriba': 0.45, 'contacto': 0.52}),
    # tu punetazo: anticipacion corta (0 -> 0,12), golpe (0,12 -> 0,20 contacto), seguimiento y vuelta.
    # En la base (MM_Attack_01) el contacto esta en 0,42 s
    'punetazo': ([(0.0, 0.18), (0.12, 0.33), (0.20, 0.42), (0.45, 0.62), (0.85, 1.0)],
                 [(0.10, 0.30, 1.3, BRAZOS + TRONCO)],
                 {'contacto': 0.20}),
    # la contra: el brazo izquierdo arriba cubriendo (0 -> 0,10), y el derecho que entra (contacto 0,22)
    'contra': ([(0.0, 0.30), (0.10, 0.36), (0.22, 0.40), (0.50, 0.62), (0.90, 1.0)],
               [(0.0, 0.30, 1.4, BRAZOS + TRONCO)],
               {'contacto': 0.22}),
    # el agarre: la parte del que agarra de la pareja de empujon, solo hasta las manos encima (y un tiron)
    # (pareja de empujon F del GASP: las manos llegan en 1,10 s; justo antes, 1,02 s, Cuttlas aun no cae)
    'agarre_guardia': ([(0.0, 0.62), (0.40, 1.02), (0.70, 1.06)], [(0.25, 0.70, 1.25, BRAZOS)], {'manos': 0.40}),
    'agarre_cuttlas': ([(0.0, 0.62), (0.40, 1.02), (0.70, 1.06)], [(0.25, 0.70, 1.15, TRONCO)], {'manos': 0.40}),
}


def base_tiempo(tramos, t):
    for (a0, b0), (a1, b1) in zip(tramos, tramos[1:]):
        if a0 <= t <= a1:
            k = (t - a0) / max(a1 - a0, 1e-6)
            k = k * k * (3 - 2 * k) if a1 - a0 > 0.2 else k   # tramos largos con entrada y salida suaves
            return b0 + (b1 - b0) * k
    return tramos[-1][1]


def factor(exag, t, hueso):
    """(factor, ventana) de la ventana que manda en t para ese hueso; (1, None) fuera de las ventanas."""
    best = (1.0, None)
    for w, (t0, t1, fac, huesos) in enumerate(exag):
        if hueso in huesos and t0 <= t <= t1:
            k = math.sin(math.pi * (t - t0) / max(t1 - t0, 1e-6))   # entra y sale suave
            f = 1.0 + (fac - 1.0) * k
            if f > best[0]:
                best = (f, w)
    return best


def exagerar(q, ref, f):
    """Aleja q de la pose de referencia (la del principio de la ventana) por el factor f, en el mapa exponencial:
    exagera el movimiento de esa ventana, no la distancia a la pose de reposo."""
    if abs(f - 1.0) < 1e-4 or ref is None:
        return q
    d = (q.normalized() @ ref.normalized().inverted()).normalized()
    if d.w < 0:
        d.negate()
    v = Vector((d.x, d.y, d.z))
    s = v.length
    if s < 1e-6:
        return q
    ang = 2 * math.atan2(s, d.w) * f
    return (Quaternion(v / s, ang) @ ref).normalized()


def main(pieza, fbx_in, fbx_out):
    tramos, exag, claves = PIEZAS[pieza]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx_in, automatic_bone_orientation=False, use_anim=True)
    arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    src = arm.animation_data.action
    sc = bpy.context.scene
    fps_base = sc.render.fps / sc.render.fps_base
    dur = tramos[-1][0]
    n = int(round(dur * FPS))
    # muestreo de la base en los tiempos remapeados
    poses = []
    for i in range(n + 1):
        t = i / FPS
        tb = base_tiempo(tramos, t)
        fr = tb * fps_base + src.frame_range[0]
        sc.frame_set(int(math.floor(fr)), subframe=fr - math.floor(fr))
        pose = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in arm.pose.bones}
        # el hueso raiz de Unreal es el propio objeto de la armadura en Blender: su movimiento (root motion) va aparte
        pose['__obj__'] = arm.matrix_world.copy()
        poses.append(pose)
    # accion nueva con las claves
    act = bpy.data.actions.new('%s_tarsis' % pieza)
    arm.animation_data.action = act
    sc.render.fps = FPS
    sc.render.fps_base = 1.0
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    arm.rotation_mode = 'QUATERNION'
    # las parejas, en el espacio de Cuttlas: su raiz (el objeto) del fotograma 0 en el origen y mirando igual
    # (agarre_cuttlas lo calcula y lo guarda; agarre_guardia aplica lo mismo, asi quedan alineados entre si)
    tw = None
    if pieza.startswith('agarre_'):
        ref = os.path.join(os.path.dirname(fbx_out), 'agarre_origen.json')
        if pieza == 'agarre_cuttlas':
            l0, r0, _ = poses[0]['__obj__'].decompose()
            tw = (Matrix.Translation(l0) @ r0.to_matrix().to_4x4()).inverted()
            json.dump([list(r) for r in tw], open(ref, 'w'))
        else:
            tw = Matrix(json.load(open(ref)))
    refs = [poses[min(len(poses) - 1, int(round(t0 * FPS)))] for (t0, t1, fac, huesos) in exag]
    for i, pose in enumerate(poses):
        t = i / FPS
        mw = pose['__obj__'] if tw is None else tw @ pose['__obj__']
        l, r, sc3 = mw.decompose()
        arm.location = l
        arm.rotation_quaternion = r
        arm.keyframe_insert('location', frame=i)
        arm.keyframe_insert('rotation_quaternion', frame=i)
        for pb in arm.pose.bones:
            loc, rot = pose[pb.name]
            pb.location = loc
            f, w = factor(exag, t, pb.name)
            pb.rotation_quaternion = exagerar(rot, refs[w][pb.name][1] if w is not None else None, f)
            pb.keyframe_insert('location', frame=i)
            pb.keyframe_insert('rotation_quaternion', frame=i)
    sc.frame_start, sc.frame_end = 0, n
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    os.makedirs(os.path.dirname(fbx_out), exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=fbx_out, use_selection=True, object_types={'ARMATURE'}, add_leaf_bones=False,
                             bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
                             armature_nodetype='NULL', primary_bone_axis='Y', secondary_bone_axis='X')
    print('[cqc] %s: %d fotogramas a %d fps (%.2f s), claves %s -> %s' % (pieza, n + 1, FPS, dur, claves, fbx_out))


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if len(args) != 3:
        sys.exit('uso: -- <pieza> <fbx_base> <fbx_salida>')
    main(*args)
