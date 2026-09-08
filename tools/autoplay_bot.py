# autoplay_bot.py -- generic tilt bot for levels nobody hand-scripted a route for.
# Python 2.5, no pygame. Steers by potential field: pulled toward the goal, pushed
# away from holes, same axis convention as game.py (screen_ax = -tilt_x).
#
#   python2.5 tools/autoplay_bot.py <level.lvl> <tilt_file> <state_file> [seconds]
#
# game.py must be run with a 5th argument (state_file) so it writes "px py vx vy"
# every frame; this bot reads that file instead of following a fixed script, which
# is what lets it attempt levels the designer model just generated. Hold the tilt
# file level for the first 3 s so game.py's calibration window sees a flat marble.
import sys, time
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import level

HOLD_LEVEL_S = 3.0
TILT_MAG = 350.0
HOLE_REPEL_RADIUS_FACTOR = 4.0
GOAL_SLOW_RADIUS_FACTOR = 3.0

def write_tilt(path, x, y, z):
    f = open(path, 'w')
    try:
        f.write('%d %d %d\n' % (x, y, z))
        f.flush()
    finally:
        f.close()

def read_state(path):
    try:
        f = open(path, 'r')
        try:
            parts = f.read().split()
        finally:
            f.close()
        return float(parts[0]), float(parts[1])
    except Exception:
        return None

def steer(px, py, lvl):
    gx, gy, gr = lvl['goal']
    dx = gx - px
    dy = gy - py
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 1.0:
        dist = 1.0
    ax = dx / dist
    ay = dy / dist
    if dist < gr * GOAL_SLOW_RADIUS_FACTOR:
        ax *= dist / (gr * GOAL_SLOW_RADIUS_FACTOR)
        ay *= dist / (gr * GOAL_SLOW_RADIUS_FACTOR)

    holes = lvl['holes']
    i = 0
    while i < len(holes):
        hx, hy, hr = holes[i]
        hdx = px - hx
        hdy = py - hy
        hdist = (hdx * hdx + hdy * hdy) ** 0.5
        repel_radius = hr * HOLE_REPEL_RADIUS_FACTOR
        if 0.0 < hdist < repel_radius:
            strength = (repel_radius - hdist) / repel_radius
            ax += (hdx / hdist) * strength
            ay += (hdy / hdist) * strength
        i += 1

    mag = (ax * ax + ay * ay) ** 0.5
    if mag > 1.0:
        ax /= mag
        ay /= mag

    # game.py: screen_ax = -tilt_x, screen_ay = -tilt_y (after dead zone), so
    # command the tilt opposite the desired screen acceleration.
    return int(-ax * TILT_MAG), int(-ay * TILT_MAG)

def main():
    if len(sys.argv) < 4:
        sys.stderr.write(
            'usage: python2.5 tools/autoplay_bot.py <level.lvl> <tilt_file> <state_file> [seconds]\n')
        return 2
    level_path = sys.argv[1]
    tilt_path = sys.argv[2]
    state_path = sys.argv[3]
    seconds = float(sys.argv[4]) if len(sys.argv) > 4 else 60.0

    lvl = level.load(level_path)
    goal = lvl['goal']

    t0 = time.time()
    while time.time() - t0 < HOLD_LEVEL_S:
        write_tilt(tilt_path, 0, 0, -1000)
        time.sleep(0.1)

    while time.time() - t0 < seconds:
        state = read_state(state_path)
        if state is None:
            write_tilt(tilt_path, 0, 0, -1000)
        else:
            px, py = state
            gx, gy, gr = goal
            gdx = px - gx
            gdy = py - gy
            if gdx * gdx + gdy * gdy <= gr * gr:
                return 0
            tx, ty = steer(px, py, lvl)
            write_tilt(tilt_path, tx, ty, -1000)
        time.sleep(0.1)
    return 0

if __name__ == '__main__':
    sys.exit(main())
