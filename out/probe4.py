"""Spike 4 (19 Oct): constrained sketch extruded with the outer profile only (islands = holes); the XZ plane fixes."""
import json, os, sys
sys.path.insert(0, '/work/tests')
import mcp_client, measure_plate as mp
from mcp_client import McpClient, save
mcp_client.OUT = '/work/out/probe4'
os.makedirs(mcp_client.OUT, exist_ok=True)
c = McpClient(['solidcraft-cli', 'mcp', '--allow-path', '/lab/out'])
c.start()


def step(name, tool, args, n=300):
    r = c.call_tool(tool, args)
    save(name, {'arguments': args, **r})
    print('==', name, 'isError' if r.get('isError') else 'ok', c.text(r)[:n].replace('\n', ' '))
    return r


cmds = [
    {'command': 'parameters.change', 'params': {'name': 'width', 'expression': '80 mm'}},
    {'command': 'sketch.create', 'params': {'plane': 'XY', 'name': 'Plate'}},
    {'command': 'sketch.rectangle.two_point', 'params': {'p0': [0, 0], 'p1': [80, 50]}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l1'], 'type': 'length', 'value': 'width'}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l4'], 'type': 'length', 'value': '50 mm'}},
]
for cid, at, d, corner in (('c1', [8, 8], 5, 'p1'), ('c2', [72, 8], 5, 'p2'), ('c3', [8, 42], 5, 'p4'), ('c4', [72, 42], 5, 'p3')):
    cmds += [{'command': 'sketch.circle.center', 'params': {'center': at, 'diameter': d}},
             {'command': 'sketch.dimension', 'params': {'entities': [cid], 'type': 'diameter', 'value': f'{d} mm'}},
             {'command': 'sketch.dimension', 'params': {'entities': [corner, f'{cid}.center'], 'type': 'horizontal', 'value': '8 mm'}},
             {'command': 'sketch.dimension', 'params': {'entities': [corner, f'{cid}.center'], 'type': 'vertical', 'value': '8 mm'}}]
cmds += [{'command': 'sketch.circle.center', 'params': {'center': [40, 25], 'diameter': 12}},
         {'command': 'sketch.dimension', 'params': {'entities': ['c5'], 'type': 'diameter', 'value': '12 mm'}},
         {'command': 'sketch.dimension', 'params': {'entities': ['p1', 'c5.center'], 'type': 'horizontal', 'value': 'width / 2'}},
         {'command': 'sketch.dimension', 'params': {'entities': ['p1', 'c5.center'], 'type': 'vertical', 'value': '25 mm'}},
         {'command': 'sketch.finish', 'params': {}},
         {'command': 'solid.extrude', 'params': {'distance': '5 mm', 'body_name': 'Plate', 'profiles': [{'curves': ['l1', 'l2', 'l3', 'l4']}]}}]
step('B_build', 'batch', {'commands': cmds})
for w in (80, 120, 60):
    if w != 80:
        step(f'B_set_{w}', 'set_parameter', {'name': 'width', 'value': f'{w} mm'}, 200)
    p = f'/lab/out/B-{w}.stl'
    step(f'B_export_{w}', 'export', {'path': p, 'format': 'stl'}, 80)
    m = mp.plate_measure(mp.read_stl(p)); s = mp.score_plate(m, w)
    print('   measured B', w, json.dumps(m)[:260], 'PASS' if s['pass'] else s['failures'])

# XZ plane: a wall X 0..80, Y 0..5, Z 0..40, then one 6 mm hole from a sketch point "at (40, 20)" on the XZ plane
WALL = [{'command': 'sketch.create', 'params': {'plane': 'XY', 'name': 'Wall'}},
        {'command': 'sketch.rectangle.two_point', 'params': {'p0': [0, 0], 'p1': [80, 5]}},
        {'command': 'sketch.finish', 'params': {}},
        {'command': 'solid.extrude', 'params': {'distance': '40 mm', 'body_name': 'Wall'}}]
VARIANTS = {
    'plain_y+20': ({'plane': 'XZ'}, [40, 20]),
    'draw_y-20': ({'plane': 'XZ'}, [40, -20]),
    'flip_true': ({'plane': 'XZ', 'flip': True}, [40, 20]),
    'flip_x': ({'plane': 'XZ', 'flip': 'x'}, [40, 20]),
    'flip_y': ({'plane': 'XZ', 'flip': 'y'}, [40, 20]),
    'explicit_axes': ({'plane': {'origin': [0, 0, 0], 'x_dir': [1, 0, 0], 'y_dir': [0, 0, 1]}}, [40, 20]),
}
for name, (sk, pt) in VARIANTS.items():
    step(f'X_{name}_new', 'new_design', {}, 40)
    r = step(f'X_{name}', 'batch', {'commands': WALL + [
        {'command': 'sketch.create', 'params': {**sk, 'name': 'HoleSketch'}},
        {'command': 'sketch.point', 'params': {'point': pt}},
        {'command': 'sketch.finish', 'params': {}},
        {'command': 'solid.hole', 'params': {'sketch': 'HoleSketch', 'diameter': 6}}]}, 120)
    body = c.text_json(r)
    last = body['results'][-1] if isinstance(body, dict) and body.get('results') else body
    p = f'/lab/out/X-{name}.stl'
    step(f'X_{name}_export', 'export', {'path': p, 'format': 'stl'}, 40)
    tris = mp.read_stl(p)
    print('   ', name, 'holes (x, z, d):', mp.holes(tris, 'y'), 'volume', round(mp.volume(tris), 1),
          'hole reply changed_bodies:', last.get('changed_bodies') if isinstance(last, dict) else '?')
c.close()
