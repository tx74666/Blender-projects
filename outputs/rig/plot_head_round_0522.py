"""Before/after orthographic plots from the verified X head widget geometry."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).parent
data = json.loads((root/'head_round_0522_validation.json').read_text())
im = Image.new('RGB',(1800,1120),'#f8fafc')
d = ImageDraw.Draw(im)
font = lambda size:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',size)
d.text((42,24),'Head control | softened depth corners',font=font(34),fill='#203650')
lo,hi=data['fit']['bounds']
center=[(a+b)*.5 for a,b in zip(lo,hi)]
views=[('FRONT',lambda p:(p[0],p[2])),('SIDE',lambda p:(-p[1],p[2])),
       ('PERSPECTIVE',lambda p:(.78*p[0]-.63*p[1],p[2]+.22*p[0]+.27*p[1]))]
scale=1400
for row,key in enumerate(('before','after')):
    d.text((42,92+row*492), 'Before' if row==0 else 'After',font=font(26),fill='#526175')
    g=data[key]
    for col,(title,proj) in enumerate(views):
        ox,oy=300+col*590,365+row*492
        d.text((70+col*590,137+row*492),title,font=font(19),fill='#64748b')
        def pixel(p):
            x,y=proj([p[i]-center[i] for i in range(3)])
            return ox+x*scale,oy-y*scale
        points=[pixel(p) for p in g['vertices']]
        for a,b in g['edges']:
            d.line([points[a],points[b]],fill='#8a98a9' if row==0 else '#258da0',width=3)
d.text((42,1070),'Same fitted dimensions, open face and head pivot. Geometry projections; not a viewport screenshot.',font=font(20),fill='#64748b')
im.save(root/'head_round_0522_comparison.png')
print(root/'head_round_0522_comparison.png')
