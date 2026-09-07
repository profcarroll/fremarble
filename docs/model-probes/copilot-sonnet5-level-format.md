=== FILE: levels/FORMAT.md
```markdown
# Tilt Levels file format (.lvl)

Plain text, one directive per line. No JSON, no nesting. Parsed with
`str.split()` only. Blank lines and lines starting with `#` are ignored.
Screen is 800x480 px, origin (0,0) at top-left. Marble radius is a fixed
game constant (18 px), not stored per level.

Directives (all values are numbers unless noted):

    NAME <text>              rest of line is the level's display name
    PAR <seconds>            target completion time
    START <x> <y>            marble spawn point (once)
    GOAL <x> <y> <radius>    goal circle (once)
    WALL <x> <y> <w> <h>     one axis-aligned wall rect (repeatable)
    HOLE <x> <y> <radius>    one deadly hole circle (repeatable)

x,y for WALL is its top-left corner. Order of directives does not matter.
Unknown directives are ignored (forward compatible).

## Worked example

    NAME Corner Test
    PAR 15
    START 60 60
    GOAL 700 400 20
    WALL 0 0 800 40
    WALL 0 200 800 40
    HOLE 650 220 18

This describes a short corridor between two horizontal walls (y 40-200),
a hole near the goal, and a 15 second par time.
```

=== FILE: levels/001-first-tilt.lvl
```
# First Tilt - corridor with two turns and one hole near the goal
NAME First Tilt
PAR 20
START 80 100
GOAL 700 340 20
WALL 0 0 800 40
WALL 0 40 40 440
WALL 40 160 480 320
WALL 640 40 160 240
WALL 760 280 40 120
WALL 640 400 160 80
WALL 520 400 120 80
HOLE 650 320 20
```

=== FILE: level.py
```python
# level.py - load and validate Tilt Levels .lvl files
# Python 2.5 safe: no json, no with, no print(), no dict comprehensions.

SCREEN_W = 800
SCREEN_H = 480
MARBLE_RADIUS = 18


def load(path):
    f = open(path, 'r')
    try:
        lines = f.readlines()
    finally:
        f.close()

    level = {
        'name': '',
        'par': 0.0,
        'start': None,
        'goal': None,
        'walls': [],
        'holes': [],
    }

    for raw in lines:
        line = raw.strip()
        if not line or line[0] == '#':
            continue
        parts = line.split()
        kw = parts[0].upper()
        if kw == 'NAME':
            level['name'] = line[len(parts[0]):].strip()
        elif kw == 'PAR':
            level['par'] = float(parts[1])
        elif kw == 'START':
            level['start'] = (float(parts[1]), float(parts[2]))
        elif kw == 'GOAL':
            level['goal'] = (float(parts[1]), float(parts[2]), float(parts[3]))
        elif kw == 'WALL':
            level['walls'].append(
                (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
            )
        elif kw == 'HOLE':
            level['holes'].append(
                (float(parts[1]), float(parts[2]), float(parts[3]))
            )
        # unknown directives are ignored on purpose

    return level


def _circle_rect_overlap(cx, cy, r, rx, ry, rw, rh):
    closest_x = max(rx, min(cx, rx + rw))
    closest_y = max(ry, min(cy, ry + rh))
    dx = cx - closest_x
    dy = cy - closest_y
    return (dx * dx + dy * dy) < (r * r)


def _point_on_screen(x, y, r):
    return (x - r >= 0 and x + r <= SCREEN_W and
            y - r >= 0 and y + r <= SCREEN_H)


def _walls_leave_room(walls, r):
    errors = []
    min_gap = 2 * r
    n = len(walls)
    i = 0
    while i < n:
        j = i + 1
        while j < n:
            ax, ay, aw, ah = walls[i]
            bx, by, bw, bh = walls[j]

            # vertical stacking: x-ranges overlap, check gap between them in y
            x_overlap = ax < bx + bw and bx < ax + aw
            if x_overlap:
                if ay + ah <= by:
                    gap = by - (ay + ah)
                    if gap > 0 and gap < min_gap:
                        errors.append(
                            'walls %d and %d leave only %d px vertical gap '
                            '(marble needs %d)' % (i, j, gap, min_gap)
                        )
                elif by + bh <= ay:
                    gap = ay - (by + bh)
                    if gap > 0 and gap < min_gap:
                        errors.append(
                            'walls %d and %d leave only %d px vertical gap '
                            '(marble needs %d)' % (i, j, gap, min_gap)
                        )

            # side by side: y-ranges overlap, check gap between them in x
            y_overlap = ay < by + bh and by < ay + ah
            if y_overlap:
                if ax + aw <= bx:
                    gap = bx - (ax + aw)
                    if gap > 0 and gap < min_gap:
                        errors.append(
                            'walls %d and %d leave only %d px horizontal gap '
                            '(marble needs %d)' % (i, j, gap, min_gap)
                        )
                elif bx + bw <= ax:
                    gap = ax - (bx + bw)
                    if gap > 0 and gap < min_gap:
                        errors.append(
                            'walls %d and %d leave only %d px horizontal gap '
                            '(marble needs %d)' % (i, j, gap, min_gap)
                        )
            j = j + 1
        i = i + 1
    return errors


def validate(level):
    errors = []
    r = MARBLE_RADIUS
    walls = level.get('walls', [])

    start = level.get('start')
    if start is None:
        errors.append('missing START')
    else:
        sx, sy = start
        if not _point_on_screen(sx, sy, r):
            errors.append('START is outside the screen')
        for w in walls:
            if _circle_rect_overlap(sx, sy, r, w[0], w[1], w[2], w[3]):
                errors.append('START overlaps a wall')
                break

    goal = level.get('goal')
    if goal is None:
        errors.append('missing GOAL')
    else:
        gx, gy, gr = goal
        if not _point_on_screen(gx, gy, r):
            errors.append('GOAL is outside the screen')
        for w in walls:
            if _circle_rect_overlap(gx, gy, r, w[0], w[1], w[2], w[3]):
                errors.append('GOAL overlaps a wall')
                break

    errors.extend(_walls_leave_room(walls, r))

    return errors
```

=== FILE: test_level.py
```python
# test_level.py - load and validate the example level, print PASS/FAIL.
# Python 2.5 safe: no print(), plain string ops only.

import level

LEVEL_PATH = 'levels/001-first-tilt.lvl'


def main():
    lvl = level.load(LEVEL_PATH)
    errors = level.validate(lvl)

    if errors:
        print 'FAIL: %s' % LEVEL_PATH
        for e in errors:
            print '  - %s' % e
    else:
        print 'PASS: %s (%s)' % (LEVEL_PATH, lvl['name'])


if __name__ == '__main__':
    main()
```

