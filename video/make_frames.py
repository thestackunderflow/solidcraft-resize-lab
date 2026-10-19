"""Annotated frames for the video from the demo renders (out/demo/*/*.png). Red dashed circles = where the spec puts a
hole that the part doesn't have. Pixel scale comes from the plate's own outline in each render (dark pixels' bounding box).
    docker run --rm -v <lab>:/w -w /w python:3.12-slim sh -c "pip -q install pillow numpy; apt-get ... fonts-dejavu-core; python video/make_frames.py"
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = '/w/out/demo'
OUT = '/w/video'
F = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
RED, INK, MUTED, GREEN = (200, 30, 30), (26, 34, 48), (91, 102, 120), (30, 122, 76)
sys.path.insert(0, '/w/tests')
import measure_plate as mp


def plate_box(img):
    a = np.asarray(img.convert('L'))
    ys, xs = np.nonzero(a < 90)
    return xs.min(), ys.min(), xs.max(), ys.max()


def to_px(box, w_mm, h_mm, x, y):
    x0, y0, x1, y1 = box
    return x0 + (x1 - x0) * x / w_mm, y1 - (y1 - y0) * y / h_mm  # y up in the top / front view


def dashed_circle(d, cx, cy, r, color=RED, width=5, n=28):
    for k in range(n):
        if k % 2:
            continue
        a0, a1 = 360 * k / n, 360 * (k + 1) / n
        d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=color, width=width)


def annotate_missing(img, w_mm, h_mm, want, got):
    """Draw a red dashed circle for each spec hole the part doesn't have (within 0.2 mm)."""
    img = img.convert('RGB')
    d = ImageDraw.Draw(img)
    box = plate_box(img)
    s = (box[2] - box[0]) / w_mm
    for (x, y, dia) in want:
        if not any(math.hypot(g[0] - x, g[1] - y) < 0.2 and abs(g[2] - dia) < 0.2 for g in got):
            cx, cy = to_px(box, w_mm, h_mm, x, y)
            dashed_circle(d, cx, cy, dia / 2 * s + 6)
    return img


def text(d, xy, s, size, color=INK, bold=False, anchor='la'):
    d.text(xy, s, font=ImageFont.truetype(FB if bold else F, size), fill=color, anchor=anchor)


def crop_plate(img, pad=60):
    x0, y0, x1, y1 = plate_box(img)
    return img.crop((max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad)))


def holes_of(tag, w):
    return mp.holes(mp.read_stl(f'/w/out/lab-out/demo-{tag}-{w}.stl'), 'z')


def panel(path, tag, w, title, sub, title_color):
    img = Image.open(path)
    img = annotate_missing(img, w, 50, mp.spec_holes(w), holes_of(tag, w))
    return crop_plate(img), title, sub, title_color


def compare(left, right, head, foot, out, size=(1920, 1080)):
    W, H = size
    can = Image.new('RGB', size, (246, 247, 249))
    d = ImageDraw.Draw(can)
    text(d, (W // 2, 70), head, 52, bold=True, anchor='mm')
    for i, (im, title, sub, col) in enumerate((left, right)):
        cx = W // 4 + i * W // 2
        text(d, (cx, 170), title, 44, col, True, 'mm')
        text(d, (cx, 225), sub, 30, MUTED, False, 'mm')
        k = min((W // 2 - 80) / im.width, (H - 380) / im.height)
        im2 = im.resize((int(im.width * k), int(im.height * k)))
        can.paste(im2, (cx - im2.width // 2, 270))
    text(d, (W // 2, H - 40), foot, 26, MUTED, False, 'mm')
    can.save(out)


os.makedirs(OUT, exist_ok=True)
FOOT = 'SolidCraft 0.16.2 · our lab, no AI, every call logged · red dashed = where the hole should be · 19 Oct 2026'
compare(panel(f'{D}/hard-coded/hard-60.png', 'hard', 60, 'Typed numbers', '2 holes gone, 1 off-centre', RED),
        panel(f'{D}/constrained/constrained-60.png', 'constrained', 60, 'Tied to the edges', 'every hole where it should be', GREEN),
        'Same change: width 80 → 60 mm', FOOT, f'{OUT}/compare-60.png')
compare(panel(f'{D}/hard-coded/hard-120.png', 'hard', 120, 'Typed numbers', 'holes stayed where 80 mm put them', RED),
        panel(f'{D}/constrained/constrained-120.png', 'constrained', 120, 'Tied to the edges', 'corners 8 mm in, big hole centred', GREEN),
        'Same change: width 80 → 120 mm', FOOT, f'{OUT}/compare-120.png')

# the XZ plane: a point drawn at sketch y = +20 vs y = -20 (front view: X right, Z up)
def xz_panel(name, title, sub, col):
    img = Image.open(f'{D}/xz-plane/xz-{name}.png').convert('RGB')
    got = mp.holes(mp.read_stl(f'/w/out/lab-out/demo-xz-{name}.stl'), 'y')
    img = annotate_missing(img, 80, 40, [(40, 20, 6)], got)
    return crop_plate(img), title, sub, col


compare(xz_panel('plain_y+20', 'Point at y = +20', 'no hole: it landed 20 mm below the floor', RED),
        xz_panel('draw_y-20', 'Point at y = −20', 'hole 20 mm up, where we wanted it', GREEN),
        'A sketch on the XZ plane: its y axis points down', 'SolidCraft 0.16.2 · front view, X right, Z up · our lab, no AI · 19 Oct 2026',
        f'{OUT}/compare-xz.png')

# Short frame 0 (1080x1920): the broken 60 mm plate, big
im = panel(f'{D}/hard-coded/hard-60.png', 'hard', 60, '', '', RED)[0]
can = Image.new('RGB', (1080, 1920), (246, 247, 249))
d = ImageDraw.Draw(can)
text(d, (540, 300), 'Width 80 → 60 mm', 72, INK, True, 'mm')
text(d, (540, 400), 'two holes are gone', 64, RED, True, 'mm')
k = 980 / im.width
im2 = im.resize((980, int(im.height * k)))
can.paste(im2, (50, 560))
text(d, (540, 560 + im2.height + 90), 'red dashed = where they should be', 40, MUTED, False, 'mm')
text(d, (540, 1780), 'SolidCraft 0.16.2 · our lab, no AI', 34, MUTED, False, 'mm')
can.save(f'{OUT}/short-frame0.png')
print('ok', os.listdir(OUT))
