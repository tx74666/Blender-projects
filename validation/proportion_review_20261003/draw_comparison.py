"""Analytical front projection using saved Basis and reference-empty placement."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent
data = json.loads((OUT / 'saved_structure.json').read_text(encoding='utf-8'))
ref = next(v for v in data['references'] if v['object'] == 'Front')
source = Image.open(ref['resolved']).convert('RGB')
height = ref['empty_display_size'] * ref['matrix_world'][2][1]
width = height * source.width / source.height
x0 = ref['matrix_world'][0][3] - width / 2
ztop = ref['matrix_world'][2][3] + height / 2
scale = source.height / height
font = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 17)
small = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 13)
canvas = Image.new('RGB', (1530, 986), '#f5f7fa')
canvas.paste(source, (0, 50))
draw = ImageDraw.Draw(canvas)
draw.text((12, 14), '项目正视参考图', fill='#26364a', font=font)
draw.text((522, 14), '保存的 Basis 与 Rest 骨骼', fill='#26364a', font=font)
draw.text((1032, 14), '按场景原有参考位置叠加', fill='#26364a', font=font)
body = data['meshes']['Cosha']
def project(v, panel):
    return (panel * 510 + (v[0] - x0) * scale, 50 + (ztop - v[2]) * scale)
body_panel = Image.new('RGB', (510, 916), '#f5f7fa')
bd = ImageDraw.Draw(body_panel)
for face in sorted(body['faces'], key=lambda f: -sum(body['vertices'][i][1] for i in f) / len(f)):
    p = [((body['vertices'][i][0]-x0)*scale, (ztop-body['vertices'][i][2])*scale) for i in face]
    bd.polygon(p, fill='#cad4e1', outline='#96a8bd')
canvas.paste(body_panel, (510, 50))
layer = Image.new('RGBA', source.size, (0, 0, 0, 0))
ld = ImageDraw.Draw(layer)
for face in body['faces']:
    pts = [((body['vertices'][i][0]-x0)*scale, (ztop-body['vertices'][i][2])*scale) for i in face]
    ld.polygon(pts, fill=(38, 85, 142, 55))
composite = Image.alpha_composite(source.convert('RGBA'), layer).convert('RGB')
canvas.paste(composite, (1020, 50))
draw = ImageDraw.Draw(canvas)
names = ('Hips', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R', 'foot.L', 'foot.R')
for panel in (1, 2):
    for name in names:
        b = data['bones'][name]
        a, c = project(b['head'], panel), project(b['tail'], panel)
        draw.line([a, c], fill='#b63785', width=3)
        for p in (a, c):
            draw.ellipse((p[0]-3, p[1]-3, p[0]+3, p[1]+3), fill='#b63785')
    for edge in data['meshes']['Dress']['edges']:
        draw.line([project(data['meshes']['Dress']['vertices'][i], panel) for i in edge], fill='#794bae', width=1)
mid = [v for v in body['vertices'] if abs(v[0]) < 1e-4 and 0.9 < v[2] < 1.2]
bridge = min(mid, key=lambda v:v[2])
landmarks = [('裙腰上缘', max(v[2] for v in data['meshes']['Dress']['vertices']), '#794bae'),
             ('大腿转轴', data['bones']['thigh.L']['head'][2], '#b63785'),
             ('胯底中央点', bridge[2], '#237476'),
             ('膝关节', data['bones']['thigh.L']['tail'][2], '#b63785')]
for label, z, colour in landmarks:
    for panel in (1, 2):
        y = project((0, 0, z), panel)[1]
        draw.line((panel*510+35, y, panel*510+475, y), fill=colour, width=1)
        if panel == 1:
            draw.rectangle((panel*510+3, y-19, panel*510+163, y-3), fill='#f5f7fa')
            draw.text((panel*510+5, y-19), label, fill=colour, font=small)
draw.text((12, 969), '只读对照：原画遮住胯部，不能直接确定其高度；脚部存在鞋子与裸脚差异；未读取当前未保存编辑。', fill='#344459', font=small)
canvas.save(OUT / 'front_comparison.png')
print(str(OUT / 'front_comparison.png'))
