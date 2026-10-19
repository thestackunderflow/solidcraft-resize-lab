"""No-AI demo sessions for the video, logged through the same JSON-RPC proxy as the agent runs (so the video's panels
cite real log lines): the hard-coded plate, the constrained plate, and the XZ-plane variants. Also renders PNGs.
    docker compose run --rm solidcraft-tests python3 tests/demo_sessions.py
Writes out/demo/<name>/transcript.jsonl (+ PNGs) and out/lab-out/demo-*.stl."""
import base64, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import builds, measure_plate as mp
from mcp_client import McpClient

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'demo')
SHOT = {'view': 'top', 'width': 1280, 'height': 800, 'grid': False, 'axes': False}


def session(name):
    d = os.path.join(ROOT, name)
    os.makedirs(d, exist_ok=True)
    log = os.path.join(d, 'transcript.jsonl')
    if os.path.exists(log):
        os.remove(log)
    c = McpClient(['python3', '/work/proxy/mcp_log_proxy.py', '--log', log, '--png-dir', d, '--',
                   'solidcraft-cli', 'mcp', '--allow-path', '/lab/out'])
    c.start()
    return c, d


def png(c, d, name, args=SHOT):
    r = c.call_tool('screenshot', args)
    img = next(x for x in r['content'] if x.get('type') == 'image')
    open(os.path.join(d, name + '.png'), 'wb').write(base64.b64decode(img['data']))


def export(c, tag, w):
    p = f'/lab/out/demo-{tag}-{w}.stl'
    c.tool_json('export', {'path': p, 'format': 'stl'})
    m = mp.plate_measure(mp.read_stl(p))
    return m, mp.score_plate(m, w)


def main():
    summary = {}
    c, d = session('hard-coded')
    c.call_tool('batch', {'commands': builds.HARD_CODED})
    for w in (80, 120, 60):
        if w != 80:
            c.tool_json('set_parameter', {'name': 'width', 'value': f'{w} mm'})
        summary[f'hard-{w}'] = export(c, 'hard', w)
        png(c, d, f'hard-{w}')
    c.tool_json('inspect_design', {'sketches': False})
    c.close()

    c, d = session('constrained')
    c.call_tool('batch', {'commands': builds.CONSTRAINED_SKETCH})
    c.tool_json('execute', {'command': 'sketch.solve', 'params': {}})
    c.call_tool('batch', {'commands': builds.CONSTRAINED_SOLID})
    for w in (80, 120, 60):
        if w != 80:
            c.tool_json('set_parameter', {'name': 'width', 'value': f'{w} mm'})
        summary[f'constrained-{w}'] = export(c, 'constrained', w)
        png(c, d, f'constrained-{w}')
    c.close()

    c, d = session('xz-plane')
    for name in builds.XZ_VARIANTS:
        c.tool_json('new_design', {})
        c.call_tool('batch', {'commands': builds.xz_commands(name)})
        p = f'/lab/out/demo-xz-{name}.stl'
        c.tool_json('export', {'path': p, 'format': 'stl'})
        summary[f'xz-{name}'] = mp.holes(mp.read_stl(p), 'y')
        png(c, d, f'xz-{name}', {**SHOT, 'view': 'front'})
    c.close()
    json.dump(summary, open(os.path.join(ROOT, 'SUMMARY.json'), 'w'), indent=1, default=str)
    for k, v in summary.items():
        print(k, v[1]['pass'] if isinstance(v, tuple) else v)


if __name__ == '__main__':
    main()
