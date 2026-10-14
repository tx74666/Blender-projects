import bpy,json
bone=bpy.data.objects['CoshaRig'].data.bones['forearm.L']
print(json.dumps({name:{'readonly':bone.bl_rna.properties[name].is_readonly,'runtime':bone.bl_rna.properties[name].is_runtime,'value':getattr(bone,name)} for name in ('use_connect','use_deform','use_inherit_rotation')}))
