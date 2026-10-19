"""The fixed SolidCraft batches the tests build (no AI). Spec: see measure_plate.py."""

_OUTLINE = [
    {'command': 'parameters.change', 'params': {'name': 'width', 'expression': '80 mm'}},
    {'command': 'sketch.create', 'params': {'plane': 'XY', 'name': 'Plate'}},
    # returns sides bottom l1, right l2, top l3, left l4; corners bottom_left p1, bottom_right p2, top_right p3, top_left p4
    {'command': 'sketch.rectangle.two_point', 'params': {'p0': [0, 0], 'p1': [80, 50]}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l1'], 'type': 'length', 'value': 'width'}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l4'], 'type': 'length', 'value': '50 mm'}},
]

# the outline follows the width; the holes are typed as numbers worked out for an 80 mm plate
HARD_CODED = _OUTLINE + [
    {'command': 'sketch.finish', 'params': {}},
    {'command': 'solid.extrude', 'params': {'distance': '5 mm', 'body_name': 'Plate'}},
] + [{'command': 'solid.hole', 'params': {'position': p, 'diameter': d}}
     for p, d in (([8, 8, 5], 5), ([72, 8, 5], 5), ([8, 42, 5], 5), ([72, 42, 5], 5), ([40, 25, 5], 12))]


def _corner_hole(cid, at, corner):
    """A 5 mm circle dimensioned 8 mm across and 8 mm up/down from the outline corner it belongs to."""
    return [{'command': 'sketch.circle.center', 'params': {'center': at, 'diameter': 5}},
            {'command': 'sketch.dimension', 'params': {'entities': [cid], 'type': 'diameter', 'value': '5 mm'}},
            {'command': 'sketch.dimension', 'params': {'entities': [corner, f'{cid}.center'], 'type': 'horizontal', 'value': '8 mm'}},
            {'command': 'sketch.dimension', 'params': {'entities': [corner, f'{cid}.center'], 'type': 'vertical', 'value': '8 mm'}}]


# one sketch: every hole tied to a corner of the outline, the centre hole to width / 2
CONSTRAINED_SKETCH = _OUTLINE + \
    _corner_hole('c1', [8, 8], 'p1') + _corner_hole('c2', [72, 8], 'p2') + \
    _corner_hole('c3', [8, 42], 'p4') + _corner_hole('c4', [72, 42], 'p3') + [
    {'command': 'sketch.circle.center', 'params': {'center': [40, 25], 'diameter': 12}},
    {'command': 'sketch.dimension', 'params': {'entities': ['c5'], 'type': 'diameter', 'value': '12 mm'}},
    {'command': 'sketch.dimension', 'params': {'entities': ['p1', 'c5.center'], 'type': 'horizontal', 'value': 'width / 2'}},
    {'command': 'sketch.dimension', 'params': {'entities': ['p1', 'c5.center'], 'type': 'vertical', 'value': '25 mm'}},
]
# the outer profile only (its islands become the holes); the default would also fill the five circles back in
CONSTRAINED_SOLID = [
    {'command': 'sketch.finish', 'params': {}},
    {'command': 'solid.extrude', 'params': {'distance': '5 mm', 'body_name': 'Plate', 'profiles': [{'curves': ['l1', 'l2', 'l3', 'l4']}]}},
]

# a wall X 0..80, Y 0..5, Z 0..40, then one 6 mm hole at a point on an XZ sketch
_WALL = [{'command': 'sketch.create', 'params': {'plane': 'XY', 'name': 'Wall'}},
         {'command': 'sketch.rectangle.two_point', 'params': {'p0': [0, 0], 'p1': [80, 5]}},
         {'command': 'sketch.finish', 'params': {}},
         {'command': 'solid.extrude', 'params': {'distance': '40 mm', 'body_name': 'Wall'}}]
XZ_VARIANTS = {
    'plain_y+20': ({'plane': 'XZ'}, [40, 20]),
    'draw_y-20': ({'plane': 'XZ'}, [40, -20]),
    'flip_true': ({'plane': 'XZ', 'flip': True}, [40, 20]),
    'flip_x': ({'plane': 'XZ', 'flip': 'x'}, [40, 20]),
    'flip_y': ({'plane': 'XZ', 'flip': 'y'}, [40, 20]),
    'explicit_axes': ({'plane': {'origin': [0, 0, 0], 'x_dir': [1, 0, 0], 'y_dir': [0, 0, 1]}}, [40, 20]),
}


def xz_commands(name):
    sk, pt = XZ_VARIANTS[name]
    return _WALL + [{'command': 'sketch.create', 'params': {**sk, 'name': 'HoleSketch'}},
                    {'command': 'sketch.point', 'params': {'point': pt}},
                    {'command': 'sketch.finish', 'params': {}},
                    {'command': 'solid.hole', 'params': {'sketch': 'HoleSketch', 'diameter': 6}}]
