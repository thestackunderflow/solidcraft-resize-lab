"""The logs the video cites say what the script says (written before the demo logs and the agent runs existed: red).
Runs anywhere with Python (reads files only)."""
import json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out')


def calls(path):
    L = [json.loads(l) for l in open(path, encoding='utf-8')]
    rep = {l['msg'].get('id'): l['msg'] for l in L if l['dir'] == 'server->client' and 'id' in l['msg']}
    out = []
    for l in L:
        if l['dir'] == 'client->server' and l['msg'].get('method') == 'tools/call':
            r = rep.get(l['msg']['id'], {}).get('result') or {}
            text = ''.join(c.get('text', '') for c in r.get('content', []) if c.get('type') == 'text')
            out.append((l['seq'], l['msg']['params']['name'], l['msg']['params'].get('arguments', {}), text, r.get('isError', False)))
    return out


def test_hard_coded_demo_shows_errors_empty_and_the_timeline_warning():
    cs = calls(os.path.join(OUT, 'demo', 'hard-coded', 'transcript.jsonl'))
    sets = [json.loads(t) for s, n, a, t, e in cs if n == 'set_parameter']
    assert [s['value'] for s in sets] == [120.0, 60.0] and all(s['errors'] == [] for s in sets)
    inspect = json.loads([t for s, n, a, t, e in cs if n == 'inspect_design'][-1])
    warns = [f['warning'] for f in inspect['timeline'] if f['warning']]
    assert len(warns) == 2 and all('is no longer on face' in w for w in warns)


def test_constrained_demo_solves_to_zero_dof():
    cs = calls(os.path.join(OUT, 'demo', 'constrained', 'transcript.jsonl'))
    solve = [json.loads(t) for s, n, a, t, e in cs if n == 'execute' and a.get('command') == 'sketch.solve'][0]
    assert solve['dof'] == 0


def test_xz_demo_plain_point_reports_ok_but_changes_no_body():
    cs = calls(os.path.join(OUT, 'demo', 'xz-plane', 'transcript.jsonl'))
    batches = [json.loads(t) for s, n, a, t, e in cs if n == 'batch']
    assert batches[0]['ok'] is True and batches[0]['results'][-1]['changed_bodies'] == []   # plain_y+20
    assert batches[1]['results'][-1]['changed_bodies'] == ['Wall']                           # draw_y-20


def test_six_agent_runs_scored_and_every_export_passes():
    s = json.load(open(os.path.join(OUT, 'runs', 'SCORES.json')))
    runs = {r['run']: r for r in s['runs']}
    assert set(runs) == {f'{a}-{i}' for a in ('plain', 'parametric') for i in (1, 2, 3)}
    assert all(r['all_exports_pass'] for r in runs.values())
    assert s['total_cost_usd'] < 10


def test_plain_runs_two_of_three_rebuilt_instead_of_resizing():
    s = json.load(open(os.path.join(OUT, 'runs', 'SCORES.json')))
    plain = [r for r in s['runs'] if r['arm'] == 'plain']
    assert sorted(r['new_design_calls'] for r in plain) == [0, 1, 1]


def test_no_host_path_or_token_in_the_logs():
    bad = ('C:/Users', 'C:\\Users', 'sk-ant', 'Authorization', 'OAUTH')
    for root, _, files in os.walk(OUT):
        if 'probe' in root:
            continue
        for f in files:
            if f.endswith(('.jsonl', '.json', '.txt')):
                text = open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
                assert not any(b in text for b in bad), os.path.join(root, f)
