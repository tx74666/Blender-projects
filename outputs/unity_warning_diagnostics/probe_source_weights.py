"""Read-only source-mesh probe. Never save the loaded character file."""
import hashlib
import importlib.util
import json
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import intersect_point_line

SOURCE = Path(r'D:\Blender\Projects\Character\X\X.blend')
OUT = Path(r'D:\Blender\Projects\Character\X\outputs\unity_warning_diagnostics')
spec = importlib.util.spec_from_file_location('unity_diagnostics',
    r'D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\unity_diagnostics.py')
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)

obj = bpy.data.objects.get('Cosha')
missing = diagnostics.unweighted_vertex_indices(obj)
rigs = {modifier.object for modifier in obj.modifiers
        if modifier.type == 'ARMATURE' and modifier.show_viewport
        and modifier.object and modifier.object.type == 'ARMATURE'}
weighted = [vertex for vertex in obj.data.vertices if vertex.index not in set(missing)]
rows = []
for index in missing:
    vertex = obj.data.vertices[index]
    edges = [edge.index for edge in obj.data.edges if index in edge.vertices]
    faces = [face.index for face in obj.data.polygons if index in face.vertices]
    neighbors = sorted(weighted, key=lambda candidate: (candidate.co - vertex.co).length)[:8]
    bones = []
    world = obj.matrix_world @ vertex.co
    for rig in rigs:
        for bone in rig.data.bones:
            if not bone.use_deform or diagnostics.is_generated_control(bone):
                continue
            head, tail = rig.matrix_world @ bone.head_local, rig.matrix_world @ bone.tail_local
            projection, factor = intersect_point_line(world, head, tail)
            closest = head.lerp(tail, max(0.0, min(1.0, factor)))
            bones.append({'name': bone.name, 'rig': rig.name,
                          'segmentDistanceWorld': (world - closest).length})
    rows.append({
        'vertex': index, 'local': list(vertex.co), 'world': list(world),
        'incidentEdges': edges, 'incidentFaces': faces,
        'isLoose': not edges and not faces,
        'groups': [{'name': obj.vertex_groups[entry.group].name, 'weight': entry.weight}
                   for entry in vertex.groups],
        'nearestWeightedSourceVertices': [
            {'vertex': candidate.index, 'localDistance': (candidate.co - vertex.co).length,
             'local': list(candidate.co),
             'groups': [{'name': obj.vertex_groups[entry.group].name, 'weight': entry.weight}
                        for entry in candidate.groups if entry.weight > 1e-8]}
            for candidate in neighbors],
        'nearestDeformBones': sorted(bones, key=lambda bone: bone['segmentDistanceWorld'])[:5],
        'nonzeroArtistShapeDeltas': [
            {'shape': key.name, 'delta': list(key.data[index].co - key.relative_key.data[index].co)}
            for key in obj.data.shape_keys.key_blocks
            if (key.data[index].co - key.relative_key.data[index].co).length > 1e-8]
            if obj.data.shape_keys else [],
    })
report = {'source': str(SOURCE), 'sourceSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'object': obj.name, 'sourceVertexCount': len(obj.data.vertices),
          'missingVertexIndices': missing, 'vertices': rows, 'sourceWasSaved': False}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'cosha_unweighted_source.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
