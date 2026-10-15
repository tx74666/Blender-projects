"""Read geometry counts from the existing disposable saved-file snapshot."""
import json
from pathlib import Path
import sys
import bpy

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER))
from profile_saved_forearm import pin

source = FOLDER / 'input_snapshot.blend'
before = pin(source)
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
scene.frame_set(11)
graph = bpy.context.evaluated_depsgraph_get()
skin_names = {'Cosha', 'Clothes', 'Stocking', 'Dress', 'Shoes', 'Hair'}
rows = []
for obj in scene.objects:
    if obj.type != 'MESH':
        continue
    row = {'name': obj.name, 'character_skin': obj.name in skin_names,
           'visible_in_saved_view_layer': obj.visible_get(),
           'base_vertices': len(obj.data.vertices), 'base_faces': len(obj.data.polygons),
           'base_triangles': sum(max(0, len(face.vertices)-2) for face in obj.data.polygons),
           'modifiers': [{'name': mod.name, 'type': mod.type, 'viewport': mod.show_viewport,
                         **({'levels': mod.levels, 'render_levels': mod.render_levels}
                            if mod.type == 'SUBSURF' else {})} for mod in obj.modifiers]}
    if row['character_skin'] or row['visible_in_saved_view_layer']:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            row.update(evaluated_vertices=len(mesh.vertices), evaluated_faces=len(mesh.polygons),
                       evaluated_triangles=len(mesh.loop_triangles))
        finally:
            evaluated.to_mesh_clear()
    rows.append(row)
report = {'schema': 'x.character-geometry-counts/1', 'completed': True,
          'input': before, 'blender': bpy.app.version_string, 'frame': scene.frame_current,
          'objects': rows, 'character_totals': {
              key: sum(row.get(key,0) for row in rows if row['character_skin'])
              for key in ('base_vertices','base_faces','base_triangles',
                          'evaluated_vertices','evaluated_faces','evaluated_triangles')},
          'limits': ['Saved snapshot only; live unsaved artist changes excluded.',
                     'Native modifiers evaluated; no add-on runtime registered and no physical solver started.',
                     'Face counts and triangle counts are distinct; hidden design assets are listed separately.'],
          'input_unchanged': pin(source) == before, 'no_scene_save': True}
assert report['input_unchanged']
(FOLDER / 'geometry_count_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
print(json.dumps({'completed':True,'character_totals':report['character_totals']},ensure_ascii=False),flush=True)
