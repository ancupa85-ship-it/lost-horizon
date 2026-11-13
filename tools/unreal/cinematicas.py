"""Crea las cinemáticas de Tarsis con Sequencer en /Game/Tarsis/Cine (ejecutar en el editor, con el nivel Tarsis abierto).

  LS_Entrada  sobrevuelo de la base (unos 14 s) que acaba en los ojos del jugador (PlayerStart)
  LS_Salida   final por el control de salida (esquina sureste): la cámara se aleja y sube
  LS_Marisma  final «EL QUE NO ENTREGO»: desde el agua, la cámara se va por la marisma hacia el oeste

ATarsisDirector las carga por su ruta y las reproduce; si no existen, el juego va igual sin ellas.
Coordenadas en cm de UE: celda (c, r) -> ((c + .5) * 200, (r + .5) * 200). La base ocupa x 0-7200, y 0-5600.
"""
import unreal

RUTA = '/Game/Tarsis/Cine'
FPS = 30
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
CENTRO = unreal.Vector(3600, 2800, 150)


def mira(desde, hacia):
    return unreal.MathLibrary.find_look_at_rotation(desde, hacia)


def jugador():
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in sub.get_all_level_actors():
        if isinstance(a, unreal.PlayerStart):
            return a.get_actor_location() + unreal.Vector(0, 0, 64), a.get_actor_rotation()
    return unreal.Vector(600, 600, 170), unreal.Rotator(0, 0, 0)


def binding_id(seq, cam):
    # la API cambió entre versiones: se prueban las dos formas
    try:
        return unreal.MovieSceneSequenceExtensions.get_portable_binding_id(seq, seq, cam)
    except Exception:
        return seq.get_binding_id(cam)


def secuencia(nombre, seg, claves, focal=24.0, fundido=None):
    """claves: lista de (segundo, Vector posición, Rotator). fundido: (segundo inicio, opacidad final) o None."""
    if eal.does_asset_exist('%s/%s' % (RUTA, nombre)):
        eal.delete_asset('%s/%s' % (RUTA, nombre))
    seq = tools.create_asset(nombre, RUTA, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    fin = int(seg * FPS)
    seq.set_display_rate(unreal.FrameRate(FPS, 1))
    seq.set_playback_start(0)
    seq.set_playback_end(fin)

    cam = seq.add_spawnable_from_class(unreal.CineCameraActor)
    plantilla = cam.get_object_template()
    # en 5.8 get_cine_camera_component() da None sobre la plantilla del spawnable
    cc = plantilla.get_cine_camera_component() or plantilla.get_editor_property('camera_component')
    cc.set_editor_property('current_focal_length', focal)
    fs = cc.get_editor_property('focus_settings')
    fs.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
    cc.set_editor_property('focus_settings', fs)

    tr = cam.add_track(unreal.MovieScene3DTransformTrack)
    sec = tr.add_section()
    sec.set_range(0, fin)
    ch = sec.get_all_channels()   # loc x y z, rot roll pitch yaw, escala x y z
    yaw_prev = None
    for t, p, r in claves:
        f = unreal.FrameNumber(int(round(t * FPS)))
        yaw = r.yaw
        if yaw_prev is not None:   # sin vueltas de 360 entre claves
            while yaw - yaw_prev > 180: yaw -= 360
            while yaw - yaw_prev < -180: yaw += 360
        yaw_prev = yaw
        for c, v in zip(ch[:6], (p.x, p.y, p.z, r.roll, r.pitch, yaw)):
            c.add_key(f, v, interpolation=unreal.MovieSceneKeyInterpolation.AUTO)

    cut = seq.add_track(unreal.MovieSceneCameraCutTrack)
    cs = cut.add_section()
    cs.set_range(0, fin)
    cs.set_camera_binding_id(binding_id(seq, cam))

    if fundido:
        try:
            ft = seq.add_track(unreal.MovieSceneFadeTrack)
            fsec = ft.add_section()
            fsec.set_range(0, fin)
            fc = fsec.get_all_channels()[0]
            fc.add_key(unreal.FrameNumber(int(fundido[0] * FPS)), 0.0)
            fc.add_key(unreal.FrameNumber(fin), fundido[1])
        except Exception as e:
            unreal.log_warning('fundido de %s: %s' % (nombre, e))

    eal.save_loaded_asset(seq)
    unreal.log('cinematica %s: %d s, %d claves' % (nombre, seg, len(claves)))
    return seq


# ---- entrada: desde la marisma, vuelta alta a la base y bajada a los ojos del jugador
ojo, rot_ojo = jugador()
puntos = [
    (0.0, unreal.Vector(-2500, 7800, 2600)),
    (4.0, unreal.Vector(3600, 8600, 2000)),
    (8.0, unreal.Vector(9200, 4200, 1600)),
]
claves = [(t, p, mira(p, CENTRO)) for t, p in puntos]
# acercamiento: a 3,5 m del jugador, por detrás y por encima, mirando hacia donde él mira
# (a 6 m y +350 caía sobre la esquina del muro perimetral, base_muro z 465)
atras = unreal.MathLibrary.get_forward_vector(rot_ojo) * -350 + unreal.Vector(0, 0, 300)
cerca = ojo + atras
claves.append((11.5, cerca, mira(cerca, ojo + unreal.MathLibrary.get_forward_vector(rot_ojo) * 400)))
claves.append((14.0, ojo, unreal.Rotator(roll=0, pitch=rot_ojo.pitch, yaw=rot_ojo.yaw)))
secuencia('LS_Entrada', 14, claves, focal=22.0)

# ---- salida (G, celda 34,26): de cerca del control a un plano alto de la base que se oscurece
salida = unreal.Vector(6900, 5300, 120)
# desde dentro, por el pasillo de la fila 26 hacia la barrera (fuera, el muro perimetral z 465 tapa; desde el noroeste, la torre 2)
p0 = unreal.Vector(6150, 5200, 230)
p1 = unreal.Vector(6300, 4950, 500)
p2 = unreal.Vector(10500, 8800, 2600)
secuencia('LS_Salida', 10, [
    (0.0, p0, mira(p0, salida)),
    (4.0, p1, mira(p1, unreal.Vector(6780, 5060, 120))),   # a la barrera
    (10.0, p2, mira(p2, CENTRO)),
], focal=28.0, fundido=(6.0, 0.7))

# ---- marisma (portillo en 310, 4900): desde el agua, la cámara se aleja hacia el oeste
portillo = unreal.Vector(310, 4900, 100)
m0 = unreal.Vector(-900, 5200, 400)   # más cerca, el muro exterior llena el plano de negro
m1 = unreal.Vector(-1500, 5300, 320)
m2 = unreal.Vector(-4200, 5900, 1100)
secuencia('LS_Marisma', 10, [
    (0.0, m0, mira(m0, portillo)),
    (4.0, m1, mira(m1, portillo)),
    (10.0, m2, mira(m2, CENTRO)),
], focal=30.0, fundido=(6.5, 0.7))
