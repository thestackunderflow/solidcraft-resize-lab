"""Spike 3 (19 Oct): does SolidCraft flag the holes the hard-coded plate loses at 60 mm? And the fully constrained sketch."""
import json, os, sys
sys.path.insert(0, '/work/tests')
import mcp_client, measure_plate as mp
from mcp_client import McpClient, save
mcp_client.OUT = '/work/out/probe3'
os.makedirs(mcp_client.OUT, exist_ok=True)
c = McpClient(['solidcraft-cli', 'mcp', '--allow-path', '/lab/out'])
c.start()


def step(name, tool, args, n=500):
    r = c.call_tool(tool, args)
    save(name, {'arguments': args, **r})
    print('==', name, 'isError' if r.get('isError') else 'ok', c.text(r)[:n].replace('\n', ' '))
    return r


def export_measure(tag, w):
    p = f'/lab/out/{tag}-{w}.stl'
    step(f'{tag}_export_{w}', 'export', {'path': p, 'format': 'stl'}, 100)
    m = mp.plate_measure(mp.read_stl(p))
    s = mp.score_plate(m, w)
    print('   measured', tag, w, json.dumps(m)[:300], 'PASS' if s['pass'] else s['failures'])


HARD = [
    {'command': 'parameters.change', 'params': {'name': 'width', 'expression': '80 mm'}},
    {'command': 'sketch.create', 'params': {'plane': 'XY', 'name': 'Plate'}},
    {'command': 'sketch.rectangle.two_point', 'params': {'p0': [0, 0], 'p1': [80, 50]}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l1'], 'type': 'length', 'value': 'width'}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l4'], 'type': 'length', 'value': '50 mm'}},
    {'command': 'sketch.finish', 'params': {}},
    {'command': 'solid.extrude', 'params': {'distance': '5 mm', 'body_name': 'Plate'}},
] + [{'command': 'solid.hole', 'params': {'position': p, 'diameter': d}}
     for p, d in (([8, 8, 5], 5), ([72, 8, 5], 5), ([8, 42, 5], 5), ([72, 42, 5], 5), ([40, 25, 5], 12))]
step('A1_build', 'batch', {'commands': HARD}, 80)
step('A_set_60', 'set_parameter', {'name': 'width', 'value': '60 mm'})
step('A_inspect_60', 'inspect_design', {}, 2500)

# B: the fully constrained sketch: every hole dimensioned from a corner of the rectangle or from the width
step('B0_new', 'new_design', {}, 80)
dims = [('l1', None, 'length', 'width'), ('l4', None, 'length', '50 mm')]
cmds = [
    {'command': 'parameters.change', 'params': {'name': 'width', 'expression': '80 mm'}},
    {'command': 'sketch.create', 'params': {'plane': 'XY', 'name': 'Plate'}},
    {'command': 'sketch.rectangle.two_point', 'params': {'p0': [0, 0], 'p1': [80, 50]}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l1'], 'type': 'length', 'value': 'width'}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l4'], 'type': 'length', 'value': '50 mm'}},
]
holes = [('c1', [8, 8], 5, 'p1'), ('c2', [72, 8], 5, 'p2'), ('c3', [8, 42], 5, 'p4'), ('c4', [72, 42], 5, 'p3')]
for cid, at, d, corner in holes:
    cmds += [{'command': 'sketch.circle.center', 'params': {'center': at, 'diameter': d}},
             {'command': 'sketch.dimension', 'params': {'entities': [cid], 'type': 'diameter', 'value': f'{d} mm'}},
             {'command': 'sketch.dimension', 'params': {'entities': [corner, f'{cid}.center'], 'type': 'horizontal', 'value': '8 mm'}},
             {'command': 'sketch.dimension', 'params': {'entities': [corner, f'{cid}.center'], 'type': 'vertical', 'value': '8 mm'}}]
cmds += [{'command': 'sketch.circle.center', 'params': {'center': [40, 25], 'diameter': 12}},
         {'command': 'sketch.dimension', 'params': {'entities': ['c5'], 'type': 'diameter', 'value': '12 mm'}},
         {'command': 'sketch.dimension', 'params': {'entities': ['p1', 'c5.center'], 'type': 'horizontal', 'value': 'width / 2'}},
         {'command': 'sketch.dimension', 'params': {'entities': ['p1', 'c5.center'], 'type': 'vertical', 'value': '25 mm'}}]
step('B1_sketch', 'batch', {'commands': cmds}, 200)
step('B2_solve', 'execute', {'command': 'sketch.solve', 'params': {}})
step('B3_solid', 'batch', {'commands': [
    {'command': 'sketch.finish', 'params': {}},
    {'command': 'solid.extrude', 'params': {'distance': '5 mm', 'body_name': 'Plate'}}]}, 300)
export_measure('B', 80)
for w in (120, 60):
    step(f'B_set_{w}', 'set_parameter', {'name': 'width', 'value': f'{w} mm'}, 200)
    export_measure('B', w)
c.close()
