"""SolidCraft 0.16.2, no AI: a sketch on the XZ plane. The docs give that plane's normal as +Y; with sketch x = world +X,
a right-handed sketch then has its y axis along world -Z. A point drawn at sketch (40, +20) is therefore 20 mm BELOW the
floor. Each fix is measured: a 6 mm hole drilled at that point through a wall X 0..80, Y 0..5, Z 0..40 must land at
world (x 40, z 20). Written before builds.py (red), then run green."""
import os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_plate as mp
import mcp_client
from mcp_client import McpClient, save
import builds

# variant -> (does the hole land at world x 40, z 20?)
EXPECT = {'plain_y+20': False, 'draw_y-20': True, 'flip_true': True, 'flip_x': True, 'flip_y': False, 'explicit_axes': True}


@pytest.fixture(scope='module')
def mcp():
    mcp_client.OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'xz-plane')
    os.makedirs(mcp_client.OUT, exist_ok=True)
    c = McpClient(['solidcraft-cli', 'mcp', '--allow-path', '/lab/out'])
    c.start()
    yield c
    c.close()


def test_every_variant_is_tested():
    assert set(builds.XZ_VARIANTS) == set(EXPECT)


@pytest.mark.parametrize('name', list(EXPECT))
def test_where_the_hole_lands(mcp, name):
    mcp.tool_json('new_design', {})
    r = mcp.call_tool('batch', {'commands': builds.xz_commands(name)})
    save(f'{name}_batch', r)
    body = mcp.text_json(r)
    assert body['ok'] is True  # every variant "succeeds"
    p = f'/lab/out/xz-{name}.stl'
    mcp.tool_json('export', {'path': p, 'format': 'stl'})
    found = mp.holes(mp.read_stl(p), 'y')
    save(f'{name}_measure', {'holes_x_z_d': found})
    hit = any(abs(h[0] - 40) < 0.1 and abs(h[1] - 20) < 0.1 and abs(h[2] - 6) < 0.1 for h in found)
    assert hit is EXPECT[name], found
    changed = body['results'][-1]['changed_bodies']
    assert (changed == ['Wall']) is EXPECT[name]  # a miss reports ok with changed_bodies: []
