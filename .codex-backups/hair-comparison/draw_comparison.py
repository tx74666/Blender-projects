"""Orthographic technical illustration from the two real Blender result files."""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

directory = Path(__file__).resolve().parent
rows = json.loads((directory / "plot-data.json").read_text(encoding="utf-8"))
SS = 2
W, H = 1600, 1080
image = Image.new("RGB", (W * SS, H * SS), "#f3f5f8")
draw = ImageDraw.Draw(image)
font_path = "C:/Windows/Fonts/msyh.ttc"

def font(size):
    return ImageFont.truetype(font_path, int(size * SS))

def text(position, value, size=24, color="#233144"):
    draw.text(tuple(int(x * SS) for x in position), value, font=font(size), fill=color)

def rect(box, fill, outline=None, radius=0):
    box = tuple(int(value * SS) for value in box)
    if radius:
        draw.rounded_rectangle(box, radius=int(radius * SS), fill=fill, outline=outline, width=SS)
    else:
        draw.rectangle(box, fill=fill, outline=outline, width=SS)

text((62, 44), "同一片後髮，兩種骨骼配置", 40)
text((65, 104), "實際 Hair2 的 6 束髮絲  ·  相同視角與比例  ·  綁定靜止姿勢", 22, "#637084")

selected = {i for chain in rows[0]["chains"] for i in chain["vertices"]}
points = [rows[0]["coordinates"][i] for i in selected]
average = tuple(sum(point[axis] for point in points) / len(points) for axis in range(3))
cxx = sum((p[0] - average[0]) ** 2 for p in points)
cyy = sum((p[1] - average[1]) ** 2 for p in points)
cxy = sum((p[0] - average[0]) * (p[1] - average[1]) for p in points)
angle = 0.5 * math.atan2(2 * cxy, cxx - cyy)
u = (math.cos(angle), math.sin(angle), 0)
depth = (-u[1], u[0], 0)
v = (-0.12 * depth[0], -0.12 * depth[1], 1)
vlength = math.sqrt(sum(value * value for value in v))
v = tuple(value / vlength for value in v)
n = (u[1] * v[2], -u[0] * v[2], u[0] * v[1] - u[1] * v[0])

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def project(point):
    relative = tuple(a - b for a, b in zip(point, average))
    return dot(relative, u), dot(relative, v), dot(relative, n)

projected = [project(point) for point in points]
for row in rows:
    for chain in row["chains"]:
        projected.extend(project(point) for bone in chain["bones"] for point in bone)
xmin, xmax = min(p[0] for p in projected), max(p[0] for p in projected)
ymin, ymax = min(p[1] for p in projected), max(p[1] for p in projected)
scale = min(605 / (xmax - xmin), 632 / (ymax - ymin))
cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
palette = ((31, 116, 201), (29, 145, 142), (72, 157, 84), (202, 128, 29), (204, 86, 110), (124, 87, 189))

for panel, row in enumerate(rows):
    left = 62 + panel * 756
    rect((left, 163, left + 718, 971), "#ffffff", "#dbe1e8", 20)
    text((left + 26, 186), "A  逐束模式" if panel == 0 else "B  分組模式", 31)
    text((left + 28, 239), "6 條鏈 · 18 根骨骼" if panel == 0 else "2 條鏈 · 6 根骨骼", 27, "#526173")
    pane = Image.new("RGB", (676 * SS, 661 * SS), "#ffffff")
    pen = ImageDraw.Draw(pane)

    def screen(point):
        x, y, _ = project(point)
        return ((338 + (x - cx) * scale) * SS, (330 - (y - cy) * scale) * SS)

    coords = row["coordinates"]
    memberships = [set(chain["vertices"]) for chain in row["chains"]]
    faces = sorted(row["faces"], key=lambda face: sum(project(coords[i])[2] for i in face) / len(face))
    for face in faces:
        owner = next((index for index, vertices in enumerate(memberships) if all(i in vertices for i in face)), None)
        color = palette[owner if panel == 0 else (0 if owner == 0 else 5)] if owner is not None else (167, 177, 188)
        p, q, r = [coords[i] for i in face[:3]]
        first, second = [a - b for a, b in zip(q, p)], [a - b for a, b in zip(r, p)]
        normal = (first[1] * second[2] - first[2] * second[1], first[2] * second[0] - first[0] * second[2], first[0] * second[1] - first[1] * second[0])
        normal_length = math.sqrt(dot(normal, normal)) or 1
        light = abs(dot(normal, n) / normal_length)
        fraction = (0.18 if owner is not None else 0.075) + 0.14 * light
        fill = tuple(round(255 * (1 - fraction) + component * fraction) for component in color)
        border = tuple(round(component * 0.83) for component in fill)
        screen_face = [screen(coords[index]) for index in face]
        pen.polygon(screen_face, fill=fill)
        pen.line(screen_face + screen_face[:1], fill=border, width=SS)
    # Draw owned hair bones only, with a narrow white outline for visibility.
    for index, chain in enumerate(row["chains"]):
        color = palette[index if panel == 0 else (0 if index == 0 else 5)]
        for head, tail in chain["bones"]:
            a, b = screen(head), screen(tail)
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            width = min(7 * SS, max(3 * SS, length * 0.075))
            ox, oy = -dy / length * width, dx / length * width
            center = a[0] + dx * 0.23, a[1] + dy * 0.23
            shape = [a, (center[0] + ox, center[1] + oy), b, (center[0] - ox, center[1] - oy)]
            pen.line([a, b], fill="white", width=11 * SS)
            pen.polygon(shape, fill=color)
            pen.line(shape + shape[:1], fill=tuple(int(c * 0.7) for c in color), width=SS)
            radius = 3 * SS
            pen.ellipse((a[0] - radius, a[1] - radius, a[0] + radius, a[1] + radius), fill="white", outline=color, width=SS)
        radius = 3 * SS
        pen.ellipse((b[0] - radius, b[1] - radius, b[0] + radius, b[1] + radius), fill="white", outline=color, width=SS)
    image.paste(pane, ((left + 21) * SS, 296 * SS))

text((65, 999), "色彩標示共用控制鏈的髮束；灰色為周圍頭髮。", 21, "#637084")
text((65, 1032), "此圖比較骨骼配置；開啟兩個 Blender 檔案，旋轉控制骨骼可比較動態效果。", 19, "#748092")
image.resize((W, H), Image.Resampling.LANCZOS).save(directory / "Hair-A-vs-B.png")
print("HAIR_COMPARISON_PNG_OK")
