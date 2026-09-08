#!/usr/bin/env python3
"""design_prompt.py -- build a prompt asking qwen3-coder for one .lvl file.

Laptop-side only (never deployed to the N900). Combines levels/FORMAT.md with a
difficulty tier from the ladder below and, optionally, a one-line telemetry
verdict from the previous tier's play attempt, so the pack gets harder (or
backs off) based on how it was actually played instead of on a fixed schedule.

    python3 tools/design_prompt.py --tier 2 --name 002-narrow-turn
    python3 tools/design_prompt.py --tier 3 --feedback "tier 2: 4s over par, 0 deaths -- too easy, raise the challenge"
"""
import argparse
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMAT_PATH = os.path.join(REPO_ROOT, 'levels', 'FORMAT.md')

# Each tier is a difficulty description in terms the .lvl format can actually
# express (walls and holes only -- no ramps, funnels or timers in this format).
DIFFICULTY_LADDER = [
    'TIER 1 (easy): one or two turns, corridor at least 120px wide, at most one '
    'hole and it sits well off the direct path, generous par time.',
    'TIER 2 (medium): three or four turns, corridor 70-100px wide, two or three '
    'holes placed near turns where the marble is already moving fast, tighter par.',
    'TIER 3 (hard): five or more turns, corridor 50-60px wide (minimum survivable '
    'gap is 36px), a hole cluster guarding the goal, at least one dead-end branch '
    'off the true path, tight par.',
    'TIER 4 (expert): everything in TIER 3 plus a second false path that looks '
    'shorter but ends in a hole, holes flanking the goal entrance on both sides, '
    'very tight par.',
]


def build_prompt(tier, name, feedback):
    fmt = open(FORMAT_PATH).read()
    difficulty = DIFFICULTY_LADDER[tier - 1]
    lines = []
    lines.append('You are designing one level for "Tilt Levels", a Marble Madness-style '
                  'tilt game. Screen is 800x480px, origin top-left, marble radius 18px.')
    lines.append('')
    lines.append('Output ONLY the level file, using this exact format (no markdown fences, '
                  'no commentary before or after):')
    lines.append('')
    lines.append(fmt.strip())
    lines.append('')
    lines.append('Difficulty target: ' + difficulty)
    if feedback:
        lines.append('')
        lines.append('Feedback from the last level played: ' + feedback)
    lines.append('')
    lines.append('Rules: the START point and the GOAL circle must not overlap any WALL, both '
                  'must be fully on screen, and every gap between walls the marble must pass '
                  'through must be at least 36px (2x marble radius). Use the NAME directive: ' +
                  (name or ('tier-%d' % tier)) + '.')
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tier', type=int, required=True, choices=range(1, len(DIFFICULTY_LADDER) + 1))
    ap.add_argument('--name', default=None, help='suggested NAME for the level')
    ap.add_argument('--feedback', default=None, help='one-line verdict from the previous tier')
    ap.add_argument('-o', '--output', default=None, help='write prompt to a file instead of stdout')
    args = ap.parse_args()

    prompt = build_prompt(args.tier, args.name, args.feedback)
    if args.output:
        open(args.output, 'w').write(prompt)
    else:
        print(prompt)


if __name__ == '__main__':
    main()
