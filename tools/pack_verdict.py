#!/usr/bin/env python3
"""pack_verdict.py -- turn one game.py RESULT line into feedback for the next tier.

    python3 tools/query_designer.py ... | python3 tools/pack_verdict.py --tier 2

Reads a "RESULT outcome=... elapsed=... deaths=... par=... frames=... avg_fps=..."
line from stdin (that is what game.py prints when a run ends) and prints one line
of feedback meant to be passed straight to design_prompt.py's --feedback flag.
"""
import re
import sys

RESULT_RE = re.compile(
    r'RESULT outcome=(\S+) elapsed=([\d.]+) deaths=(\d+) par=([\d.]+)')


def verdict(tier, outcome, elapsed, deaths, par):
    if outcome != 'goal':
        return 'tier %d: bot did not finish (%s) -- too hard, ease up' % (tier, outcome)
    ratio = elapsed / par if par > 0 else 1.0
    if deaths >= 3 or ratio > 1.5:
        return 'tier %d: finished in %.1fs vs par %.0fs with %d deaths -- too hard, ease up' % (
            tier, elapsed, par, deaths)
    if deaths == 0 and ratio < 0.6:
        return 'tier %d: finished in %.1fs vs par %.0fs with 0 deaths -- too easy, raise the challenge' % (
            tier, elapsed, par)
    return 'tier %d: finished in %.1fs vs par %.0fs with %d deaths -- about right, hold steady' % (
        tier, elapsed, par, deaths)


def main():
    tier = 1
    if '--tier' in sys.argv:
        tier = int(sys.argv[sys.argv.index('--tier') + 1])

    line = ''
    for raw in sys.stdin:
        if raw.startswith('RESULT'):
            line = raw
    m = RESULT_RE.search(line)
    if not m:
        sys.stderr.write('no RESULT line found on stdin\n')
        return 2
    outcome, elapsed, deaths, par = m.group(1), float(m.group(2)), int(m.group(3)), float(m.group(4))
    print(verdict(tier, outcome, elapsed, deaths, par))
    return 0


if __name__ == '__main__':
    sys.exit(main())
