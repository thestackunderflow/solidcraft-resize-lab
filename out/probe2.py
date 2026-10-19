"""Spike 2 (19 Oct): a constrained, parameter-driven plate vs a plate with hard-coded hole positions; resize 80 -> 120 -> 60."""
import json, os, sys
sys.path.insert(0, '/work/tests')
import mcp_client, measure_plate as mp
from mcp_client import McpClient, save
mcp_client.OUT = '/work/out/probe2'
os.makedirs(mcp_client.OUT, exist_ok=True)
c = McpClient(['solidcraft-cli', 'mcp', '--allow-path', '/lab/out'])
c.start()


def step(name, tool, args):
    r = c.call_tool(tool, args)
    save(name, {'arguments': args, **r})
    print('==', name, 'isError' if r.get('isError') else 'ok', c.text(r)[:500].replace('\n', ' '))
    return r


def export_measure(tag, w):
    p = f'/lab/out/{tag}-{w}.stl'
    step(f'{tag}_export_{w}', 'export', {'path': p, 'format': 'stl'})
    m = mp.plate_measure(mp.read_stl(p))
    s = mp.score_plate(m, w)
    print('   measured', tag, w, json.dumps(m)[:300], 'PASS' if s['pass'] else s['failures'])


# --- A: hard-coded holes (positions typed as numbers for an 80 mm plate) ---
step('A1_build', 'batch', {'commands': [
    {'command': 'parameters.change', 'params': {'name': 'width', 'expression': '80 mm'}},
    {'command': 'sketch.create', 'params': {'plane': 'XY', 'name': 'Plate'}},
    {'command': 'sketch.rectangle.two_point', 'params': {'p0': [0, 0], 'p1': [80, 50]}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l1'], 'type': 'length', 'value': 'width'}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l4'], 'type': 'length', 'value': '50 mm'}},
    {'command': 'sketch.finish', 'params': {}},
    {'command': 'solid.extrude', 'params': {'distance': '5 mm', 'body_name': 'Plate'}},
    {'command': 'solid.hole', 'params': {'position': [8, 8, 5], 'diameter': 5}},
    {'command': 'solid.hole', 'params': {'position': [72, 8, 5], 'diameter': 5}},
    {'command': 'solid.hole', 'params': {'position': [8, 42, 5], 'diameter': 5}},
    {'command': 'solid.hole', 'params': {'position': [72, 42, 5], 'diameter': 5}},
    {'command': 'solid.hole', 'params': {'position': [40, 25, 5], 'diameter': 12}},
]})
export_measure('A', 80)
for w in (120, 60):
    step(f'A_set_{w}', 'set_parameter', {'name': 'width', 'value': f'{w} mm'})
    export_measure('A', w)

# --- B: one sketch, every hole dimensioned from an edge or from the width ---
step('B0_new', 'new_design', {})
r = step('B1_build', 'batch', {'commands': [
    {'command': 'parameters.change', 'params': {'name': 'width', 'expression': '80 mm'}},
    {'command': 'sketch.create', 'params': {'plane': 'XY', 'name': 'Plate'}},
    {'command': 'sketch.rectangle.two_point', 'params': {'p0': [0, 0], 'p1': [80, 50]}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l1'], 'type': 'length', 'value': 'width'}},
    {'command': 'sketch.dimension', 'params': {'entities': ['l4'], 'type': 'length', 'value': '50 mm'}},
    {'command': 'sketch.circle.center', 'params': {'center': [8, 8], 'diameter': 5}},
]})
c.close()
