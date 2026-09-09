"""Full-width orthographic rear view of actual Hair3 mirrored mesh/rest bones."""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

directory = Path(__file__).resolve().parents[2] / "Previews"
data = json.loads((Path(__file__).resolve().parent / "Hair3_Full_Mirror_0.40.2-plot-data.json").read_text(encoding="utf-8"))
SS = 2
W, H = 1400, 1170
image = Image.new("RGB", (W * SS, H * SS), "#f4f6f8")
draw = ImageDraw.Draw(image)
palette = {"L": (77, 124, 162), "R": (144, 110, 166), "C": (217, 128, 39)}

def font(size):
    return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", int(size * SS))

def text(position, value, size=24, color="#2c394b", anchor=None):
    draw.text(tuple(int(x * SS) for x in position), value, font=font(size), fill=color, anchor=anchor)

text((65, 43), "Hair3 · 完整對稱髮骨", 43)
text((67, 109), "6 條左側鏈 + 1 條中央鏈 + 6 條右側鏈 = 13 條鏈 / 52 根髮骨", 25, "#617084")
draw.rounded_rectangle((61 * SS, 176 * SS, 1339 * SS, 1055 * SS), 22 * SS, fill="white", outline="#dce2e9", width=SS)
for x, side, label in ((288, "L", "L · 6 條鏈"), (700, "C", "C · 1 條鏈"), (1112, "R", "R · 6 條鏈")):
    text((x, 216), label, 27, palette[side], anchor="mm")

points = data["coordinates"]
all_points = points + [point for chain in data["chains"] for bone in chain["bones"] for point in bone]
# Camera faces -Y from the rear (+Y). X is reversed on screen, as in Blender's rear orthographic view.
xmin, xmax = min(-p[0] for p in all_points), max(-p[0] for p in all_points)
zmin, zmax = min(p[2] for p in all_points), max(p[2] for p in all_points)
scale = min(1135 / (xmax - xmin), 738 / (zmax - zmin))
center_x, center_z = (xmin + xmax) / 2, (zmin + zmax) / 2

def screen(point):
    return ((700 + (-point[0] - center_x) * scale) * SS,
            (653 - (point[2] - center_z) * scale) * SS)

faces = sorted(data["faces"], key=lambda face: sum(points[i][1] for i in face) / len(face))
for face in faces:
    p, q, r = [points[i] for i in face[:3]]
    a, b = [x - y for x, y in zip(q, p)], [x - y for x, y in zip(r, p)]
    normal = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    length = math.sqrt(sum(value * value for value in normal)) or 1
    light = abs(normal[1] / length)
    tone = round(247 - 29 * light)
    fill = (tone, min(255, tone + 2), min(255, tone + 4))
    outline = tuple(component - 9 for component in fill)
    polygon = [screen(points[i]) for i in face]
    draw.polygon(polygon, fill=fill)
    draw.line(polygon + polygon[:1], fill=outline, width=1)

# A quiet reference line makes it possible to inspect the central chain's location.
seam_x = screen(data["seam_world"])[0]
for y in range(273 * SS, 1030 * SS, 14 * SS):
    draw.line([(seam_x, y), (seam_x, y + 7 * SS)], fill="#c8ccd1", width=SS)

for chain in sorted(data["chains"], key=lambda chain: chain["side"] == "C"):
    color = palette[chain["side"]]
    for head, tail in chain["bones"]:
        a, b = screen(head), screen(tail)
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        assert length > 1e-6
        width = min(7 * SS, max(2.4 * SS, length * 0.07))
        ox, oy = -dy / length * width, dx / length * width
        middle = a[0] + dx * 0.23, a[1] + dy * 0.23
        shape = [a, (middle[0] + ox, middle[1] + oy), b, (middle[0] - ox, middle[1] - oy)]
        draw.line([a, b], fill="white", width=(9 if chain["side"] == "C" else 7) * SS)
        draw.polygon(shape, fill=color)
        draw.line(shape + shape[:1], fill=tuple(int(component * 0.7) for component in color), width=SS)
        radius = (3.2 if chain["side"] == "C" else 2.6) * SS
        draw.ellipse((a[0] - radius, a[1] - radius, a[0] + radius, a[1] + radius), fill="white", outline=color, width=SS)
    draw.ellipse((b[0] - radius, b[1] - radius, b[0] + radius, b[1] + radius), fill="white", outline=color, width=SS)

text((65, 1090), "正後視圖 · 完整 Mirror 網格 · 每條鏈 4 根骨骼", 24, "#627085")
text((65, 1131), "中央橙色單鏈沿中縫排列；左右髮束均有骨骼鏈。", 22, "#738093")
output = directory / "Hair3_Full_Mirror_0.40.2.png"
image.resize((W, H), Image.Resampling.LANCZOS).save(output)
print("FULL_HAIR3_PNG_OK", str(output))
