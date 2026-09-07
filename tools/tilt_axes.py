# tilt_axes.py -- confirm the accelerometer-to-screen mapping with a hand on the device.
# Python 2.5, no pygame.  Run it over SSH and tilt the N900 while watching the output:
#
#   python2.5 tools/tilt_axes.py [seconds] [tilt_source]
#
# It runs the game's own input pipeline (0.5 s "level" calibration, 3-sample mean, soft
# dead zone, axis mapping) and prints, ten times a second, the raw coord line and the
# direction the marble would roll.  Hold the device still for the first half second.
#
#   raw   18  -468  -756 | tilt x  +12  y -432 | marble: DOWN 392    (rolls toward the low edge)
#
# Tilt the right edge down and the line must say RIGHT; bottom edge down must say DOWN.
# If it says UP/DOWN when you tilt left/right the axes are transposed again (BUG-002).
import sys, time
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import game

def main():
    seconds = 20.0
    src = game.ACCEL
    if len(sys.argv) > 1:
        seconds = float(sys.argv[1])
    if len(sys.argv) > 2:
        src = sys.argv[2]

    sys.stdout.write('tilt source: %s  (%.0f s; hold still for the first %.1f s)\n' % (
        src, seconds, game.CALIBRATION_WINDOW))
    last = (0, 0, -1000)
    t0 = time.time()
    sum_x = 0.0
    sum_y = 0.0
    count = 0
    level_x = 0.0
    level_y = 0.0
    calibrated = 0
    history = []
    while time.time() - t0 < seconds:
        last = game.read_tilt(src, last)
        x, y, z = last
        now = time.time()
        if not calibrated:
            sum_x += x
            sum_y += y
            count += 1
            if now - t0 >= game.CALIBRATION_WINDOW:
                level_x = sum_x / count
                level_y = sum_y / count
                calibrated = 1
                sys.stdout.write('level = (%.0f, %.0f) mg; now tilt.\n' % (level_x, level_y))
            time.sleep(0.1)
            continue
        history.append((x - level_x, y - level_y))
        if len(history) > 3:
            del history[0]
        mx = 0.0
        my = 0.0
        i = 0
        while i < len(history):
            mx += history[i][0]
            my += history[i][1]
            i += 1
        tilt_x = game.apply_dead_zone(mx / len(history))
        tilt_y = game.apply_dead_zone(my / len(history))
        screen_ax = -tilt_x
        screen_ay = -tilt_y
        words = []
        if screen_ax > 0:
            words.append('RIGHT %.0f' % screen_ax)
        elif screen_ax < 0:
            words.append('LEFT %.0f' % -screen_ax)
        if screen_ay > 0:
            words.append('DOWN %.0f' % screen_ay)
        elif screen_ay < 0:
            words.append('UP %.0f' % -screen_ay)
        if not words:
            words.append('still')
        sys.stdout.write('raw %5d %5d %5d | tilt x %+5.0f y %+5.0f | marble: %s\n' % (
            x, y, z, tilt_x, tilt_y, '  '.join(words)))
        sys.stdout.flush()
        time.sleep(0.1)
    return 0

if __name__ == '__main__':
    sys.exit(main())
