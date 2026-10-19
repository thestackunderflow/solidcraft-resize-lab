"""STL measurer for the mounting plate: NumPy only, no CAD kernel.

The plate (the spec every build is scored against): width W along X (the parameter), depth 50 mm along Y, thickness
5 mm along Z (Z 0..5). Four 5 mm corner holes, centres 8 mm in from both edges; one 12 mm centre hole at (W/2, 25).
A hole is found from its edge vertices on a face: vertices on that face that are not on the outer boundary, grouped by
distance, then a least-squares circle through each group.
"""
import math
import struct
import numpy as np

DEPTH, THICK, INSET, CORNER_D, CENTRE_D = 50.0, 5.0, 8.0, 5.0, 12.0
TOL = 0.1  # mm


def read_stl(path):
    """Triangles as an (n, 3, 3) array; binary or ASCII STL."""
    data = open(path, 'rb').read()
    if data[:5] == b'solid' and b'facet' in data[:400]:
        v = [list(map(float, l.split()[1:4])) for l in data.decode('ascii', 'replace').splitlines() if l.strip().startswith('vertex')]
        return np.array(v).reshape(-1, 3, 3)
    n = struct.unpack('<I', data[80:84])[0]
    a = np.frombuffer(data, dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]), count=n, offset=84)
    return a['v'].reshape(-1, 3, 3).astype(float)


def bbox(tris):
    p = tris.reshape(-1, 3)
    return p.min(0), p.max(0)


def volume(tris):
    return float(np.einsum('ij,ij->i', tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum() / 6.0)


def fit_circle(pts):
    """Least-squares circle (Kasa) through 2-D points: (cx, cy, diameter)."""
    x, y = pts[:, 0], pts[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    cx, cy, c = np.linalg.lstsq(A, x * x + y * y, rcond=None)[0]
    return float(cx), float(cy), float(2 * math.sqrt(c + cx * cx + cy * cy))


def _groups(pts, gap):
    """Connected groups of 2-D points: two points join when closer than gap."""
    left, out = list(range(len(pts))), []
    while left:
        grp, todo = [left.pop()], None
        todo = list(grp)
        while todo:
            i = todo.pop()
            d = np.hypot(*(pts[left] - pts[i]).T) if left else np.array([])
            near = [left[k] for k in np.nonzero(d < gap)[0]]
            for j in near:
                left.remove(j)
            grp += near
            todo += near
        out.append(pts[grp])
    return out


def holes(tris, axis='z', gap=3.0, eps=1e-3):
    """Holes through the part along axis ('z': (x, y, d) from the top face; 'y': (x, z, d) from the y-min face)."""
    p = np.unique(np.round(tris.reshape(-1, 3), 6), axis=0)
    lo, hi = p.min(0), p.max(0)
    k = {'x': 0, 'y': 1, 'z': 2}[axis]
    face = p[np.abs(p[:, k] - (hi[k] if axis == 'z' else lo[k])) < eps]
    a, b = [i for i in range(3) if i != k]
    on_edge = (np.abs(face[:, a] - lo[a]) < eps) | (np.abs(face[:, a] - hi[a]) < eps) | \
              (np.abs(face[:, b] - lo[b]) < eps) | (np.abs(face[:, b] - hi[b]) < eps)
    inner = face[~on_edge][:, [a, b]]
    found = [fit_circle(g) for g in _groups(inner, gap) if len(g) >= 3]
    return sorted(found)


def spec_holes(w):
    """(x, y, diameter) of the five holes for width w."""
    r, t = w - INSET, DEPTH - INSET
    return [(INSET, INSET, CORNER_D), (r, INSET, CORNER_D), (INSET, t, CORNER_D), (r, t, CORNER_D), (w / 2, DEPTH / 2, CENTRE_D)]


def plate_measure(tris):
    lo, hi = bbox(tris)
    return {'bbox_min': lo.round(3).tolist(), 'bbox_max': hi.round(3).tolist(), 'volume': round(volume(tris), 2),
            'holes': [[round(v, 3) for v in h] for h in holes(tris, 'z')]}


def spec_volume(w):
    return w * DEPTH * THICK - 4 * math.pi * (CORNER_D / 2) ** 2 * THICK - math.pi * (CENTRE_D / 2) ** 2 * THICK


def score_plate(m, w):
    """Compare a measurement with the spec at width w: {'pass', 'failures'}."""
    f = []
    want_hi = [w, DEPTH, THICK]
    for i, n in enumerate('XYZ'):
        if abs(m['bbox_min'][i]) > TOL or abs(m['bbox_max'][i] - want_hi[i]) > TOL:
            f.append(f'bounding box {n}: {m["bbox_min"][i]}..{m["bbox_max"][i]}, want 0..{want_hi[i]}')
    got = list(m['holes'])
    for (x, y, d) in spec_holes(w):
        near = [h for h in got if math.hypot(h[0] - x, h[1] - y) < TOL and abs(h[2] - d) < TOL]
        if near:
            got.remove(near[0])
        else:
            f.append(f'hole {d:g} mm at ({x:g}, {y:g}) missing')
    for h in got:
        f.append(f'extra hole {h[2]:g} mm at ({h[0]:g}, {h[1]:g})')
    want_v = spec_volume(w)
    if abs(m['volume'] - want_v) > 0.005 * want_v:
        f.append(f'volume {m["volume"]} mm3, want {want_v:.1f}')
    return {'pass': not f, 'failures': f}
