# level.py - load and validate Tilt Levels .lvl files
# Python 2.5 safe: no json, no with, no print(), no dict comprehensions.

import os

SCREEN_W = 800
SCREEN_H = 480
MARBLE_RADIUS = 18


def find_levels(path):
    """Return the ordered list of .lvl files to play, given a file or directory.

    A directory is a pack: every .lvl inside it, sorted by name, played in
    order so reaching the goal advances to the next one. A single file is one
    level, played on its own -- which is how the bot and per-level telemetry
    probes stay scoped to exactly one level.
    """
    if not os.path.isdir(path):
        return [path]

    names = []
    entries = os.listdir(path)
    i = 0
    while i < len(entries):
        n = entries[i]
        if n.lower().endswith('.lvl'):
            names.append(n)
        i += 1
    names.sort()

    out = []
    i = 0
    while i < len(names):
        out.append(os.path.join(path, names[i]))
        i += 1
    return out


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
