"""Score every agent run in out/runs/: measure each exported STL against the spec at its width, count tool calls and
failures from the logged JSON-RPC, and record how the resize was done (set_parameter vs a rebuild). Writes
out/runs/SCORES.json."""
import glob, json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests'))
import measure_plate as mp

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'runs')
rows = []
for d in sorted(glob.glob(os.path.join(ROOT, '*-*'))):
    if not os.path.isdir(d):
        continue
    name = os.path.basename(d)
    meta = json.load(open(os.path.join(d, 'run-meta.json')))
    out = json.load(open(os.path.join(d, 'claude-output.json'))) if os.path.getsize(os.path.join(d, 'claude-output.json')) else {}
    lines = [json.loads(l) for l in open(os.path.join(d, 'transcript.jsonl'), encoding='utf-8')] if os.path.exists(os.path.join(d, 'transcript.jsonl')) else []
    calls = [l for l in lines if l['dir'] == 'client->server' and l['msg'].get('method') == 'tools/call']
    replies = {l['msg'].get('id'): l['msg'] for l in lines if l['dir'] == 'server->client' and 'id' in l['msg']}
    failed = [c for c in calls if (replies.get(c['msg']['id'], {}).get('result') or {}).get('isError')]
    tools = [c['msg']['params']['name'] for c in calls]
    batch_cmds = [cmd.get('command') for c in calls if c['msg']['params']['name'] == 'batch'
                  for cmd in c['msg']['params'].get('arguments', {}).get('commands', [])]
    exports = {}
    for stl in sorted(glob.glob(os.path.join(d, 'plate-*.stl'))):
        w = int(re.search(r'plate-(\d+)\.stl', stl).group(1))
        m = mp.plate_measure(mp.read_stl(stl))
        exports[w] = {'measured': m, 'score': mp.score_plate(m, w)}
    rows.append({
        'run': name, 'arm': meta['arm'], 'exit': meta['exit'], 'wall_s': meta['wall_s'], 'model': meta['model'],
        'claude_version': meta['claude_version'], 'cost_usd': out.get('total_cost_usd'), 'turns': out.get('num_turns'),
        'tool_calls': len(calls), 'failed_calls': len(failed), 'tools': tools,
        'set_parameter_calls': tools.count('set_parameter'), 'new_design_calls': tools.count('new_design'),
        'uses_sketch_dimension': 'sketch.dimension' in batch_cmds, 'uses_solid_hole': 'solid.hole' in batch_cmds,
        'exports': exports, 'all_exports_pass': bool(exports) and all(e['score']['pass'] for e in exports.values()),
        'final_text': (out.get('result') or '')[:1500],
    })
json.dump({'runs': rows, 'total_cost_usd': round(sum(r['cost_usd'] or 0 for r in rows), 4)},
          open(os.path.join(ROOT, 'SCORES.json'), 'w'), indent=1)
for r in rows:
    print(r['run'], r['cost_usd'], r['tool_calls'], 'calls', r['failed_calls'], 'failed',
          {w: e['score']['pass'] for w, e in r['exports'].items()}, 'set_param', r['set_parameter_calls'], 'new_design', r['new_design_calls'])
