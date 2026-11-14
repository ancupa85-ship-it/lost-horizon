"""Piezas de juego del perímetro nuevo (tanda 20) que no vienen en base.glb.

Se ejecuta en el editor con el nivel Tarsis abierto:  py tools/unreal/perimetro.py
- Tope_Salida: pared invisible fuera del portón de salida (1 x 8 x 4 m, centrada en 9280, 5700, 200) para que nadie
  se vaya andando por el terraplén sin acabar la misión. El punto de salida del director (ExitLoc 9050, 5700, radio
  420) queda antes del tope: con el expediente la misión acaba al llegar; sin él, sale el aviso y el tope para.
Se puede ejecutar varias veces: borra lo que puso antes (etiqueta Tope_Salida) y lo vuelve a poner.
"""
import unreal

V = unreal.Vector
CUBO = '/Engine/BasicShapes/Cube.Cube'   # 100 cm de lado
CARPETA = 'Perimetro'


def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))


def tope_salida():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.actor_has_tag('Tope_Salida'):
            eas.destroy_actor(a)
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, V(9280, 5700, 200), unreal.Rotator(0, 0, 0))
    a.set_actor_label('Tope_Salida')
    a.set_folder_path(CARPETA)
    a.tags = [unreal.Name('Tope_Salida')]
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset(CUBO))
    a.set_actor_scale3d(V(1.0, 8.0, 4.0))
    c.set_collision_profile_name('BlockAll')
    c.set_cast_shadow(False)
    a.set_actor_hidden_in_game(True)
    log('tope de la salida en', a.get_actor_location())
    return a


def todo():
    tope_salida()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


if __name__ == '__main__':
    todo()
