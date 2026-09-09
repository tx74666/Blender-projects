from pathlib import Path
p=Path(r'D:\MyRepository\Blender-addons-by-Randy\tests\test_limb_ik_fk_ui_blender.py')
text=p.read_text(encoding='utf-8')
text=text.replace('    assert not (set(side["chain"]) & {bone.name for bone in animation.bones})', '    animation = rig.data.collections["Animation"]\n    assert not (set(side["chain"]) & {bone.name for bone in animation.bones})')
exec(compile(text,str(p),'exec'), {'__name__':'__main__','__file__':str(p)})
