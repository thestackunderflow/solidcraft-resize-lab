# SolidCraft: a part that resizes without breaking (a test-first lab)

**Lab snapshot: 19 Oct 2026.** SolidCraft 0.16.2 (release tarball, SHA256SUMS checked), driven over MCP. Claude Code
2.1.303 for the agent runs. Everything runs in Docker; nothing is installed on the host.

## The part

A mounting plate: width W along X (the parameter), 50 mm deep, 5 mm thick. Four 5 mm corner holes, centres 8 mm in from
both edges; one 12 mm hole at (W/2, 25). Resized 80 → 120 → 60 mm.

## What the lab shows (no AI, `tests/`)

- `test_resize.py`: the **hard-coded** plate (outline follows `width`, holes typed as numbers) is right at 80 mm; at
  120 mm the holes stay at x = 8, 40, 72; at 60 mm the two right-hand holes are gone. `set_parameter` replies
  `errors: []` both times; the timeline's `inspect_design` carries a warning on Hole2 and Hole4 ("is no longer on face").
  The **constrained** plate (every hole dimensioned from its own corner, the centre hole at width / 2, one sketch with
  0 degrees of freedom, extruded as the outer profile) is right at all three widths.
- `test_xz_plane.py`: a point drawn at sketch (40, +20) on the XZ plane makes no hole (the batch says ok,
  `changed_bodies: []`); the hole lands at world z = 20 with: drawing at y = −20, `flip: true`, `flip: "x"`, explicit
  axes. `flip: "y"` does not fix it.
- `test_measure_plate.py`: the STL measurer (NumPy only) on synthetic meshes.
- `test_evidence.py`: the logs the video cites say what the script says; no host paths or tokens in the logs.

Red then green: `out/red-phase-*.log`, `out/green-phase-*.log`. Spikes that shaped the tests: `out/probe*.py` and
`out/probe*/`.

## Agent runs (`claude-run/`)

`run.sh plain|parametric N`: one clean headless Claude Code run (no user CLAUDE.md, no user settings, no memory; only
SolidCraft's MCP tools; every JSON-RPC line logged by `proxy/mcp_log_proxy.py`). `score.py` measures every exported STL.
Six runs, alternating, `claude-sonnet-5-5`, `--max-budget-usd 1.50` each: **all exports passed; total $0.83**
(`out/runs/SCORES.json`). Plain words: 2 of 3 rebuilt the 60 mm plate as a new design instead of resizing. Asked for a
width parameter: 3 of 3 resized with one `set_parameter`; 2 of 3 first extruded a solid slab, measured it and undid it.

## Run it

```bash
docker compose build measure-tests
docker compose run --rm measure-tests
docker compose run --rm solidcraft-tests
docker compose run --rm solidcraft-tests python3 tests/demo_sessions.py   # logged demo sessions + renders
bash claude-run/run.sh parametric 1                                        # paid: Claude Code on the host
docker compose run --rm score
```

`mcp-config.json` files show the host lab folder as `$LAB` (scrubbed by `run.sh`).
