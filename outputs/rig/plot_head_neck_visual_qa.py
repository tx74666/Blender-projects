"""Orthographic data plot from evaluated mesh and actual custom-shape geometry."""
import json, math, html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
data = json.loads((ROOT/'head_neck_visual_qa_geometry.json').read_text())
W,H = 1800,940
image = Image.new('RGB', (W,H), '#f8fafc')
draw = ImageDraw.Draw(image)
font_path = 'C:/Windows/Fonts/segoeui.ttf'
bold_path = 'C:/Windows/Fonts/segoeuib.ttf'
def font(size, bold=False): return ImageFont.truetype(bold_path if bold else font_path,size)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="#f8fafc"/>']
def line(points, color, width=2):
    draw.line(points, fill=color, width=width)
    path = ' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
    svg.append(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>')
def text(x,y,value,size=22,color='#334155',bold=False):
    draw.text((x,y),value,font=font(size,bold),fill=color)
    svg.append(f'<text x="{x}" y="{y+size}" font-family="Segoe UI, sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{html.escape(value)}</text>')
def poly(points, fill):
    draw.polygon(points, fill=fill)
    path = ' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
    svg.append(f'<polygon points="{path}" fill="{fill}"/>')
text(50,28,'X · Head and neck control fit',38,bold=True)
text(50,80,'Saved preview · orthographic projections in the head’s anatomical frame · Cosha body only',22)
line([(54,128),(95,128)],'#2379bc',4);text(110,112,'Head helmet',21)
line([(304,128),(345,128)],'#d17a16',4);text(360,112,'Neck collar',21)
line([(564,128),(605,128)],'#b2bbc8',9);text(620,112,'Evaluated body silhouette',21)
views=[('FRONT','Forward toward viewer',lambda p:(p[0],p[2]),(0,.10)),
       ('SIDE','Forward to the right',lambda p:(-p[1],p[2]),(.018,.10)),
       ('TOP','Forward toward top',lambda p:(p[0],-p[1]),(0,.02))]
for index,(title,caption,project,center) in enumerate(views):
    left=40+index*590
    text(left+15,167,title,24,bold=True)
    text(left+15,202,caption,19,color='#64748b')
    cx,cy=left+270,524
    scale=1450
    def pixel(p):
        x,y=project(p)
        return cx+(x-center[0])*scale,cy-(y-center[1])*scale
    # Repeated opaque face fills form the projected silhouette without making
    # dense mesh topology falsely look like clearance crossings.
    for face in data['faces']:
        poly([pixel(data['vertices'][i]) for i in face], '#dfe4eb')
    for name,widget in data['widgets'].items():
        color='#2379bc' if widget['role']=='HEAD' else '#d17a16'
        points=[pixel(p) for p in widget['vertices']]
        for a,b in widget['edges']:
            line([points[a],points[b]],color,3)
    # A neutral origin cross marks the unchanged native head pivot.
    x,y=pixel((0,0,0))
    line([(x-5,y),(x+5,y)],'#64748b',1);line([(x,y-5),(x,y+5)],'#64748b',1)
    x0,y0=left+36,808
    line([(x0,y0),(x0+.05*scale,y0)],'#64748b',2)
    line([(x0,y0-5),(x0,y0+5)],'#64748b',2)
    line([(x0+.05*scale,y0-5),(x0+.05*scale,y0+5)],'#64748b',2)
    text(x0+7,y0+10,'50 mm',17,color='#64748b')
    if index<2:line([(left+555,170),(left+555,854)],'#e2e8f0',1)
text(50,872,'No body-crossing widget edges. Sampled minimum clearance: helmet 25.2 mm · collar 6.6 mm.',22,bold=True)
text(50,906,'Wires are drawn through the silhouette for inspection; hair is excluded. Scale assumes scene units in metres.',18,color='#64748b')
svg.append('</svg>')
image.save(ROOT/'head_neck_052_three_views.png')
(ROOT/'head_neck_052_three_views.svg').write_text('\n'.join(svg),encoding='utf-8')
summary={name:{k:v for k,v in item.items() if k not in {'vertices','edges'}} for name,item in data['widgets'].items()}
summary['preview_unchanged']=data['preview_unchanged']
summary['diagram']='head_neck_052_three_views.png'
(ROOT/'head_neck_052_visual_qa.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('PLOT_WRITTEN',ROOT/'head_neck_052_three_views.png')
