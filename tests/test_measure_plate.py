"""The plate measurer, on synthetic meshes with known answers (written before measure_plate.py; NumPy only)."""
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_plate as mp


def box(x0, y0, z0, x1, y1, z1):
    """A closed box as 12 outward triangles."""
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return np.array([[v[a], v[b], v[c]] for a, b, c in f])


def ring(cx, cy, z, d, n=48):
    """Degenerate 'triangles' that carry a hole's edge vertices at height z (only vertices matter to holes())."""
    pts = [(cx + d / 2 * math.cos(2 * math.pi * k / n), cy + d / 2 * math.sin(2 * math.pi * k / n), z) for k in range(n)]
    return np.array([[p, p, p] for p in pts])


def plate(w, d, t, holes, axis='z'):
    tris = [box(0, 0, 0, w, d, t)]
    for (a, b, dia) in holes:
        if axis == 'z':
            tris += [ring(a, b, t, dia), ring(a, b, 0, dia)]
        else:  # holes along Y through a plate X 0..w, Y 0..d, Z 0..t: centre (x=a, z=b)
            r = ring(a, b, 0, dia)
            r = r[:, :, [0, 2, 1]]  # (x, y, z) -> (x, 0, y): the ring lies on the y=0 face
            tris += [r, r + np.array([0, d, 0])]
    return np.concatenate(tris)


def test_volume_of_a_box():
    assert abs(mp.volume(box(0, 0, 0, 80, 50, 5)) - 20000) < 1e-6


def test_bbox():
    lo, hi = mp.bbox(box(0, 0, 0, 80, 50, 5))
    assert list(lo) == [0, 0, 0] and list(hi) == [80, 50, 5]


def test_holes_through_z_found_with_centres_and_diameters():
    holes = [(8, 8, 5), (72, 8, 5), (8, 42, 5), (72, 42, 5), (40, 25, 12)]
    got = mp.holes(plate(80, 50, 5, holes), 'z')
    assert len(got) == 5
    for (a, b, dia) in holes:
        m = min(got, key=lambda h: math.hypot(h[0] - a, h[1] - b))
        assert math.hypot(m[0] - a, m[1] - b) < 1e-6 and abs(m[2] - dia) < 1e-6


def test_no_holes_in_a_plain_box():
    assert mp.holes(box(0, 0, 0, 80, 50, 5), 'z') == []


def test_holes_through_y_report_x_and_z():
    got = mp.holes(plate(80, 5, 40, [(40, 20, 6)], axis='y'), 'y')
    assert len(got) == 1 and abs(got[0][0] - 40) < 1e-6 and abs(got[0][1] - 20) < 1e-6 and abs(got[0][2] - 6) < 1e-6


def test_score_plate_passes_the_spec_and_names_each_failure():
    w = 120

    def measured(holes):  # the synthetic mesh carries hole edges, not hole volume: set the spec volume
        return {**mp.plate_measure(plate(w, 50, 5, holes)), 'volume': mp.spec_volume(w)}
    good = mp.score_plate(measured(mp.spec_holes(w)), w)
    assert good['pass'], good
    stale = mp.score_plate(measured(mp.spec_holes(80)), w)  # holes left where they were at 80
    assert not stale['pass']
    assert any('hole' in f for f in stale['failures'])


def test_spec_holes_follow_the_width():
    assert mp.spec_holes(60) == [(8, 8, 5), (52, 8, 5), (8, 42, 5), (52, 42, 5), (30, 25, 12)]
