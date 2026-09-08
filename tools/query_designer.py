#!/usr/bin/env python3
"""query_designer.py -- ask qwen3-coder on sld-cloud for one .lvl file and validate it.

Laptop-side only. Talks to Ollama's HTTP API. sld-cloud only listens on
127.0.0.1:11434, so tunnel first:

    ssh -L 11434:127.0.0.1:11434 sld-cloud

then, in another terminal:

    python3 tools/design_prompt.py --tier 1 -o /tmp/prompt.txt
    python3 tools/query_designer.py /tmp/prompt.txt levels/generated/001-tier1.lvl

This never touches the N900; it only writes a level file on the laptop for the
validator, the bot, and eventually a human to look at before it goes anywhere.
"""
import itertools
import json
import re
import sys
import threading
import time
import urllib.request

sys.path.insert(0, '.')
import level

MODEL = 'qwen3-coder:30b-a3b-q4_K_M'
OLLAMA_URL = 'http://127.0.0.1:11434/api/generate'
KNOWN_DIRECTIVES = ('NAME', 'PAR', 'START', 'GOAL', 'WALL', 'HOLE', '#')
SPINNER = '|/-\\'


def _spin(label, done):
    # cold model load on the Ampere node can take a while with nothing else to show for it
    start = time.time()
    for frame in itertools.cycle(SPINNER):
        if done.is_set():
            break
        sys.stderr.write('\r%s %s (%.0fs)  ' % (frame, label, time.time() - start))
        sys.stderr.flush()
        time.sleep(0.2)
    sys.stderr.write('\r' + ' ' * (len(label) + 20) + '\r')
    sys.stderr.flush()


def query(prompt, url=OLLAMA_URL, model=MODEL, timeout=600):
    body = json.dumps({'model': model, 'prompt': prompt, 'stream': False}).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})

    done = threading.Event()
    spinner = threading.Thread(target=_spin, args=('waiting for ' + model, done))
    spinner.start()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            reply = json.loads(resp.read().decode('utf-8'))
    finally:
        done.set()
        spinner.join()
    return reply['response']


def extract_level(text):
    """Keep only lines that look like .lvl directives, dropping any markdown
    fences or explanatory prose the model adds despite being asked not to."""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        first = re.split(r'\s+', line, maxsplit=1)[0].upper()
        if first in KNOWN_DIRECTIVES or line.startswith('#'):
            out.append(line)
    return '\n'.join(out) + '\n'


def _push_clear(x, y, r, walls, margin=4.0):
    """Nudge a point clear of any wall it overlaps, along whichever side has
    the least penetration, then clamp it back onto the screen."""
    guard = 0
    while guard < 8:
        hit = None
        for w in walls:
            if level._circle_rect_overlap(x, y, r, w[0], w[1], w[2], w[3]):
                hit = w
                break
        if hit is None:
            break
        wx, wy, ww, wh = hit
        pens = [
            ('left', (x + r) - wx),
            ('right', (wx + ww) - (x - r)),
            ('top', (y + r) - wy),
            ('bottom', (wy + wh) - (y - r)),
        ]
        side, _pen = min(pens, key=lambda p: p[1])
        if side == 'left':
            x = wx - r - margin
        elif side == 'right':
            x = wx + ww + r + margin
        elif side == 'top':
            y = wy - r - margin
        else:
            y = wy + wh + r + margin
        guard += 1
    x = max(r + margin, min(x, level.SCREEN_W - r - margin))
    y = max(r + margin, min(y, level.SCREEN_H - r - margin))
    return x, y


def auto_repair(lvl):
    """Fix the geometry mistakes the model makes most often (START/GOAL placed
    a few pixels too close to a wall) without spending another slow query on
    arithmetic. Returns True if anything was changed."""
    r = level.MARBLE_RADIUS
    walls = lvl.get('walls', [])
    changed = False

    if lvl.get('start') is not None:
        sx, sy = lvl['start']
        nx, ny = _push_clear(sx, sy, r, walls)
        if (nx, ny) != (sx, sy):
            lvl['start'] = (nx, ny)
            changed = True

    if lvl.get('goal') is not None:
        gx, gy, gr = lvl['goal']
        nx, ny = _push_clear(gx, gy, gr, walls)
        if (nx, ny) != (gx, gy):
            lvl['goal'] = (nx, ny, gr)
            changed = True

    return changed


def serialize_level(lvl):
    lines = []
    if lvl.get('name'):
        lines.append('NAME ' + lvl['name'])
    lines.append('PAR %g' % lvl['par'])
    sx, sy = lvl['start']
    lines.append('START %g %g' % (sx, sy))
    gx, gy, gr = lvl['goal']
    lines.append('GOAL %g %g %g' % (gx, gy, gr))
    for wx, wy, ww, wh in lvl['walls']:
        lines.append('WALL %g %g %g %g' % (wx, wy, ww, wh))
    for hx, hy, hr in lvl['holes']:
        lines.append('HOLE %g %g %g' % (hx, hy, hr))
    return '\n'.join(lines) + '\n'


def retry_prompt(base_prompt, errors):
    complaint = '\n'.join('- ' + e for e in errors)
    return (base_prompt + '\n\nThe previous attempt failed validation:\n' + complaint +
            '\nFix these specific problems. Output ONLY the corrected level file, '
            'same format, no commentary.')


def generate_valid_level(prompt, out_path, url=OLLAMA_URL, max_attempts=3):
    """Query, validate, and on failure re-ask with the validator's own errors
    folded in, up to max_attempts. Returns (lvl_or_None, errors, attempt_count)."""
    current_prompt = prompt
    attempt = 1
    while True:
        raw = query(current_prompt, url=url)
        lvl_text = extract_level(raw)
        open(out_path, 'w').write(lvl_text)

        lvl = level.load(out_path)
        if auto_repair(lvl):
            open(out_path, 'w').write(serialize_level(lvl))
            lvl = level.load(out_path)

        errors = level.validate(lvl)
        if not errors:
            return lvl, errors, attempt
        if attempt >= max_attempts:
            return None, errors, attempt

        sys.stdout.write('attempt %d invalid, retrying with feedback:\n' % attempt)
        for e in errors:
            sys.stdout.write('  ' + e + '\n')
        current_prompt = retry_prompt(prompt, errors)
        attempt += 1


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(
            'usage: python3 tools/query_designer.py <prompt_file> <out.lvl> [ollama_url] [max_attempts]\n')
        return 2
    prompt_path, out_path = sys.argv[1], sys.argv[2]
    url = sys.argv[3] if len(sys.argv) > 3 else OLLAMA_URL
    max_attempts = int(sys.argv[4]) if len(sys.argv) > 4 else 3

    prompt = open(prompt_path).read()
    lvl, errors, attempt = generate_valid_level(prompt, out_path, url=url, max_attempts=max_attempts)

    if lvl is None:
        sys.stdout.write('INVALID %s (after %d attempts)\n' % (out_path, attempt))
        for e in errors:
            sys.stdout.write('  ' + e + '\n')
        return 1
    sys.stdout.write('OK %s  name=%r par=%s walls=%d holes=%d  (attempt %d)\n' % (
        out_path, lvl['name'], lvl['par'], len(lvl['walls']), len(lvl['holes']), attempt))
    return 0


if __name__ == '__main__':
    sys.exit(main())
