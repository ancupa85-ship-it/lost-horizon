"""Tanda P: piezas propias del cuerpo a cuerpo, hechas en Blender a partir de animaciones de base del maniqui.

No son de Lyra tal cual: cada pieza se rehace con su propio ritmo (anticipacion, golpe, seguimiento y vuelta) y con las
poses clave exageradas, que es lo que las charlas de combate (Cooper, Sekiro, God of War) dicen que vende el golpe:
- el tiempo se remapea por tramos (TRAMOS: segundo nuevo -> segundo de la base), muestreando la base y clavando claves;
- en las ventanas de EXAGERAR, la rotacion de los huesos se aleja de la pose de reposo por un factor (mapa exponencial);
- las piezas en pareja salen en el mismo espacio: la raiz de Cuttlas en el origen y los dos con el mismo sentido.

Uso (Blender sin ventana):
  blender.exe -b --factory-startup --python tools/blender/cqc_anims.py -- <pieza> <fbx_base> <fbx_salida>
Piezas: culatazo, punetazo, contra, agarre_guardia, agarre_cuttlas (ver PIEZAS). Imprime los segundos clave para el C++.

Tanda R: las bases del punetazo y la contra (MM_Attack_01/02 de Lyra) son acometidas: la raiz avanza 151 y 90 cm. Con
ACOMETIDA, la raiz se queda en esos cm (25) y los pies se clavan con IK en sus apoyos: el pie apoyado no se mueve en el
mundo y el que va al aire llega a su sitio nuevo (lo que se le quita a la raiz se reparte en el paso). Luego se hornea.
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


# pieza -> (cm que avanza la raiz en la base, cm que se dejan)
ACOMETIDA = {'punetazo': (151.0, 25.0), 'contra': (81.0, 25.0)}   # cm medidos en la pieza (de su primer a su ultimo fotograma)


def clavar_pies(arm, n, base_cm, deja_cm):
    """Baja la acometida de la raiz (el objeto de la armadura) a deja_cm y clava los pies con IK donde se apoyaban."""
    sc = bpy.context.scene
    L = []
    for f in range(n + 1):
        sc.frame_set(f)
        L.append(arm.location.copy())
    total = (L[-1] - L[0]).length
    if total < 1e-6:
        print('[cqc] sin acometida que bajar'); return
    k = deja_cm / base_cm
    u = total / base_cm   # unidades de Blender por cm
    Lp = [L[0] + (l - L[0]) * k for l in L]
    R = [l - lp for l, lp in zip(L, Lp)]   # lo que se le quita a la raiz en cada fotograma
    # pies del original (mundo): posicion de la cabeza del pie y su giro
    F = {s_: [] for s_ in ('l', 'r')}
    Q = {s_: [] for s_ in ('l', 'r')}
    for f in range(n + 1):
        sc.frame_set(f)
        for s_ in ('l', 'r'):
            pb = arm.pose.bones['foot_' + s_]
            m = arm.matrix_world @ pb.matrix
            F[s_].append(m.translation.copy())
            Q[s_].append(m.to_quaternion())
    # apoyos: casi quieto y cerca de su altura mas baja
    O = {}
    for s_ in ('l', 'r'):
        zmin = min(p.z for p in F[s_])
        quieto = []
        for f in range(n + 1):
            a, b = F[s_][max(f - 1, 0)], F[s_][min(f + 1, n)]
            v = (b - a).length / (2.0 / FPS)
            quieto.append(v < 20 * u and F[s_][f].z < zmin + 4 * u)
        # tramos de apoyo; en cada uno el pie se queda donde estaria al final del tramo (asi la pierna se encoge en vez de
        # estirarse de mas: con la raiz atrasada, el pie de delante quedaria fuera de su alcance)
        tramos_ap = []
        f = 0
        while f <= n:
            if quieto[f]:
                g = f
                while g + 1 <= n and quieto[g + 1]:
                    g += 1
                tramos_ap.append((f, g))
                f = g + 1
            else:
                f += 1
        o = [None] * (n + 1)
        for a_, b_ in tramos_ap:
            for h in range(a_, b_ + 1):
                o[h] = R[b_].copy()
        # en el aire: del valor del apoyo de antes al del siguiente, con entrada y salida suaves
        prev_end, prev_val = -1, R[0].copy()
        idx = 0
        f = 0
        while f <= n:
            if o[f] is not None:
                prev_end, prev_val = f, o[f]
                f += 1
                continue
            g = f
            while g <= n and o[g] is None:
                g += 1
            dest = o[g] if g <= n else R[n]
            for h in range(f, g if g <= n else n + 1):
                w = (h - prev_end) / max((g if g <= n else n + 1) - prev_end, 1)
                w = w * w * (3 - 2 * w)
                o[h] = prev_val.lerp(dest, w)
            f = g
        O[s_] = o
    # la raiz nueva
    for f in range(n + 1):
        arm.location = Lp[f]
        arm.keyframe_insert('location', frame=f)
    # IK de dos huesos a mano, fotograma a fotograma (el IK de Blender no sirve aqui: en el FBX los huesos no estan unidos,
    # la cola de la pantorrilla no cae en el pie). En espacio de la armadura: rodilla en el plano de cadera, objetivo y
    # rodilla original; el pie conserva su giro del original
    for f in range(n + 1):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        inv = arm.matrix_world.inverted()
        for s_ in ('l', 'r'):
            th, ca, ft = arm.pose.bones['thigh_' + s_], arm.pose.bones['calf_' + s_], arm.pose.bones['foot_' + s_]
            Hh, K, A = th.matrix.translation.copy(), ca.matrix.translation.copy(), ft.matrix.translation.copy()
            T = inv @ (F[s_][f] - O[s_][f])
            qf = (inv.to_quaternion() @ Q[s_][f]).normalized()
            la, lb = (K - Hh).length, (A - K).length
            d = min((T - Hh).length, (la + lb) * 0.999)
            uu = (T - Hh).normalized()
            vv = (K - Hh) - uu * (K - Hh).dot(uu)
            if vv.length < 1e-6:
                vv = (A - Hh).cross(uu).cross(uu)
            vv.normalize()
            ca_ = max(-1.0, min(1.0, (la * la + d * d - lb * lb) / (2 * la * d)))
            K2 = Hh + uu * (la * ca_) + vv * (la * math.sqrt(1 - ca_ * ca_))
            r1 = (K - Hh).rotation_difference(K2 - Hh)
            th.matrix = Matrix.Translation(Hh) @ r1.to_matrix().to_4x4() @ Matrix.Translation(-Hh) @ th.matrix
            bpy.context.view_layer.update()
            K, A = ca.matrix.translation.copy(), ft.matrix.translation.copy()
            T2 = Hh + uu * d
            r2 = (A - K).rotation_difference(T2 - K)
            ca.matrix = Matrix.Translation(K) @ r2.to_matrix().to_4x4() @ Matrix.Translation(-K) @ ca.matrix
            bpy.context.view_layer.update()
            m = ft.matrix.copy()
            ft.matrix = Matrix.Translation(m.translation) @ qf.to_matrix().to_4x4() @ Matrix.Diagonal(m.to_scale()).to_4x4()
            bpy.context.view_layer.update()
            for pb in (th, ca, ft):
                pb.keyframe_insert('rotation_quaternion', frame=f)
                pb.keyframe_insert('location', frame=f)
    # comprobacion: cuanto se mueve el pie apoyado en el mundo
    peor, apoyos, falla = 0.0, [], 0.0
    for s_ in ('l', 'r'):
        ini = None
        for f in range(n + 1):
            sc.frame_set(f)
            p = (arm.matrix_world @ arm.pose.bones['foot_' + s_].matrix).translation.copy()
            falla = max(falla, (p - (F[s_][f] - O[s_][f])).length / u)
            if f > 0 and O[s_][f] == O[s_][f - 1]:
                if ini is None:
                    ini = prev
                peor = max(peor, (p - ini).length / u)
            else:
                if ini is not None:
                    apoyos.append(s_)
                ini = None
            prev = p
    print('[cqc] acometida %.0f -> %.0f cm (raiz %.1f -> %.1f u); el pie apoyado se desliza como mucho %.1f cm por apoyo (%d apoyos); el IK queda a %.1f cm de su objetivo como mucho' % (
        base_cm, deja_cm, total, (Lp[-1] - Lp[0]).length, peor, len(apoyos), falla))


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
    if pieza in ACOMETIDA:
        clavar_pies(arm, n, *ACOMETIDA[pieza])
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
