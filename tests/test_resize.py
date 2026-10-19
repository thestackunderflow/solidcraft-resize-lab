"""SolidCraft 0.16.2 over MCP, no AI: the same mounting plate built two ways, then resized 80 -> 120 -> 60 mm.
Hard-coded: the outline follows `width`, the five holes are typed as numbers for an 80 mm plate.
Constrained: one sketch, every hole dimensioned from a corner of the outline (or from the width), extruded as one profile.
Written before builds.py (red), then run green."""
import json, os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_plate as mp
import mcp_client
from mcp_client import McpClient, save
import builds

OUT = '/lab/out'


def session(name):
    mcp_client.OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'resize', name)
    os.makedirs(mcp_client.OUT, exist_ok=True)
    c = McpClient(['solidcraft-cli', 'mcp', '--allow-path', OUT])
    c.start()
    return c


def export_measure(c, tag, w):
    p = f'{OUT}/{tag}-{w}.stl'
    r = c.call_tool('export', {'path': p, 'format': 'stl'})
    save(f'export_{w}', r)
    assert not r.get('isError'), c.text(r)
    m = mp.plate_measure(mp.read_stl(p))
    s = mp.score_plate(m, w)
    save(f'measure_{w}', {'measured': m, 'score': s})
    return m, s


@pytest.fixture(scope='module')
def hard():
    c = session('hard-coded')
    r = c.call_tool('batch', {'commands': builds.HARD_CODED})
    save('build', r)
    assert c.text_json(r)['ok'] is True
    yield c
    c.close()


@pytest.fixture(scope='module')
def con():
    c = session('constrained')
    r = c.call_tool('batch', {'commands': builds.CONSTRAINED_SKETCH})
    save('build_sketch', r)
    assert c.text_json(r)['ok'] is True
    yield c
    c.close()


def test_0_version(hard):
    assert hard.init_result['serverInfo']['version'] == '0.16.2'


def test_1_hard_coded_plate_is_right_at_80(hard):
    m, s = export_measure(hard, 'hard', 80)
    assert s['pass'], s


def test_2_hard_coded_at_120_the_outline_grows_and_the_holes_stay(hard):
    r = hard.tool_json('set_parameter', {'name': 'width', 'value': '120 mm'})
    save('set_120', r)
    assert r['errors'] == []
    m, s = export_measure(hard, 'hard', 120)
    assert m['bbox_max'][0] == 120.0 and not s['pass']
    xs = sorted({round(h[0]) for h in m['holes']})
    assert xs == [8, 40, 72]  # where they were typed for 80 mm; the spec wants 8, 60, 112


def test_3_hard_coded_at_60_two_holes_vanish_and_the_reply_lists_no_errors(hard):
    r = hard.tool_json('set_parameter', {'name': 'width', 'value': '60 mm'})
    save('set_60', r)
    assert r['errors'] == [] and r['recomputed'] == 7
    m, s = export_measure(hard, 'hard', 60)
    assert len(m['holes']) == 3 and not s['pass']
    design = hard.tool_json('inspect_design', {})
    save('inspect_60', design)
    warn = {f['name']: f['warning'] for f in design['timeline'] if f.get('warning')}
    assert set(warn) == {'Hole2', 'Hole4'}
    assert all('is no longer on face' in w for w in warn.values())


def test_4_constrained_sketch_has_no_degrees_of_freedom_left(con):
    r = con.tool_json('execute', {'command': 'sketch.solve', 'params': {}})
    save('solve', r)
    assert r['dof'] == 0 and r['status'] == 'solved'
    r = con.call_tool('batch', {'commands': builds.CONSTRAINED_SOLID})
    save('build_solid', r)
    assert con.text_json(r)['ok'] is True


@pytest.mark.parametrize('w', [80, 120, 60])
def test_5_constrained_plate_is_right_at_every_width(con, w):
    if w != 80:
        r = con.tool_json('set_parameter', {'name': 'width', 'value': f'{w} mm'})
        save(f'set_{w}', r)
        assert r['errors'] == []
    m, s = export_measure(con, 'constrained', w)
    assert s['pass'], s
