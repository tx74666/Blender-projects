"""Factory-only native Geometry Nodes input ABI diagnostic; never loads assets."""
import bpy
import json

assert bpy.app.background and bpy.app.version[:2] == (5, 2) and not bpy.data.filepath
group = bpy.data.node_groups.new('QA GN input ABI', 'GeometryNodeTree')
group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
socket = group.interface.new_socket(name='Use Cloth', in_out='INPUT', socket_type='NodeSocketBool')
inp = group.nodes.new('NodeGroupInput')
out = group.nodes.new('NodeGroupOutput')
switch = group.nodes.new('GeometryNodeSwitch')
switch.input_type = 'GEOMETRY'
group.links.new(inp.outputs['Use Cloth'], switch.inputs['Switch'])
group.links.new(inp.outputs['Geometry'], switch.inputs['True'])
group.links.new(inp.outputs['Geometry'], switch.inputs['False'])
group.links.new(switch.outputs['Output'], out.inputs['Geometry'])
mesh = bpy.data.meshes.new('QA GN input ABI')
obj = bpy.data.objects.new(mesh.name, mesh)
bpy.context.scene.collection.objects.link(obj)
modifier = obj.modifiers.new('QA GN input ABI', 'NODES')
modifier.node_group = group
report = {'version': list(bpy.app.version), 'identifier': socket.identifier, 'trials': {}}
for name, getter, setter in (
        ('old_modifier_IDprops', lambda: modifier[socket.identifier], lambda: modifier.__setitem__(socket.identifier, True)),
        ('native_properties_IDprops', lambda: modifier.properties[socket.identifier], lambda: modifier.properties.__setitem__(socket.identifier, True)),
        ('native_properties_RNA', lambda: getattr(modifier.properties, socket.identifier), lambda: setattr(modifier.properties, socket.identifier, True))):
    row = {}
    try:
        row['before'] = getter()
        setter()
        row['after'] = getter()
        row['success'] = type(row['after']) is bool and row['after'] is True
    except Exception as exc:
        row['error'] = repr(exc)
        row['success'] = False
    report['trials'][name] = row
report['properties_RNA'] = [p.identifier for p in modifier.properties.bl_rna.properties]
print(json.dumps(report, sort_keys=True))
