"""Spike (19 Oct): how 0.16.2 answers the commands the resize tests need. Output: out/probe/*.json."""
import json, os, sys
sys.path.insert(0, '/work/tests')
import mcp_client
from mcp_client import McpClient, save
mcp_client.OUT = '/work/out/probe'
os.makedirs(mcp_client.OUT, exist_ok=True)

c = McpClient(['solidcraft-cli', 'mcp', '--allow-path', '/lab/out'])
c.start()


def step(name, tool, args):
    r = c.call_tool(tool, args)
    save(name, {'arguments': args, **r})
    print('==', name, 'isError' if r.get('isError') else 'ok', c.text(r)[:700].replace('\n', ' '))
    return r


step('01_rect_sketch', 'batch', {'commands': [
    {'command': 'parameters.change', 'params': {'name': 'width', 'expression': '80 mm'}},
    {'command': 'sketch.create', 'params': {'plane': 'XY', 'name': 'Plate'}},
    {'command': 'sketch.rectangle.two_point', 'params': {'p0': [0, 0], 'p1': [80, 50]}},
]})
step('02_inspect', 'execute', {'command': 'sketch.inspect', 'params': {}})
step('03_solve', 'execute', {'command': 'sketch.solve', 'params': {}})
c.close()
