import os, re, sys, time, math
import pygame
import level
from telemetry import Telemetry

ACCEL = '/sys/class/i2c-adapter/i2c-3/3-001d/coord'
VIBRATOR = '/sys/class/leds/twl4030:vibrator/brightness'

# Axis mapping, from the N900 accelerometer table (wiki.maemo.org/N900_accelerometer):
#   right edge down  -> coord x = -1000      bottom edge down -> coord y = -1000
# so device x runs along the long side of the screen and device y along the short side.
# A marble rolls toward the low edge:  screen_ax = -x_mg,  screen_ay = -y_mg.
# (Until 2026-09-07 the two axes were transposed: a left/right tilt moved the marble
# up/down. See docs/BUG-002.md.)
ACCEL_PER_MG = 1.2
DRAG = 0.8
MAX_SPEED = 900.0
RESTITUTION = 0.3
CALIBRATION_WINDOW = 0.5
TILT_DEAD_ZONE = 40.0
WALL_BUZZ_LOW = 150.0
WALL_BUZZ_HIGH = 400.0

W = level.SCREEN_W
H = level.SCREEN_H

def hole_hit(px, py, holes):
    """Return the first hole whose circle contains the marble center.
    Holes are checked in order from left to right in the list.
    Return -1 when the marble does not enter any hole.
    """
    i = 0
    while i < len(holes):
        hx, hy, hr = holes[i]
        dx = px - hx
        dy = py - hy
        if dx * dx + dy * dy < hr * hr:
            return i
        i += 1
    return -1

def apply_dead_zone(mg):
    """Soft dead zone: readings inside +/-TILT_DEAD_ZONE are zero, and the
    zone's width is subtracted outside it, so the response is continuous
    instead of jumping from 0 to 40 mg at the edge."""
    if mg > TILT_DEAD_ZONE:
        return mg - TILT_DEAD_ZONE
    if mg < -TILT_DEAD_ZONE:
        return mg + TILT_DEAD_ZONE
    return 0.0

def sanitize_name(name):
    s = re.sub('[^a-z0-9]+', '-', name.lower()).strip('-')
    return s or 'level'

def default_telemetry_path(level_path, lvl):
    base = lvl.get('name', '')
    if not base:
        base = os.path.splitext(os.path.basename(level_path))[0]
    base = sanitize_name(base)
    d = 'telemetry'
    if not os.path.isdir(d):
        os.makedirs(d)
    return os.path.join(d, base + '-' + str(int(time.time())) + '.csv')

def read_tilt(path, last):
    try:
        f = open(path, 'r')
        try:
            s = f.read()
        finally:
            f.close()
        parts = s.split()
        return int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        return last

def write_vibrator(value):
    try:
        f = open(VIBRATOR, 'w')
        try:
            f.write(value)
        finally:
            f.close()
    except Exception:
        pass

def buzz_vibrator(now, duration_ms, vibrate_until, vibrator_on):
    until = now + duration_ms / 1000.0
    if until > vibrate_until:
        vibrate_until = until
    if not vibrator_on:
        write_vibrator('255')
        vibrator_on = 1
    return vibrate_until, vibrator_on

def update_vibrator(now, vibrate_until, vibrator_on):
    if vibrator_on and now >= vibrate_until:
        write_vibrator('0')
        vibrator_on = 0
    return vibrator_on

def wall_buzz_duration(speed):
    if speed > WALL_BUZZ_HIGH:
        return 80
    if speed > WALL_BUZZ_LOW:
        return 40
    return 0

def build_background(lvl):
    bg = pygame.Surface((W, H)).convert()
    bg.fill((20, 24, 30))
    walls = []
    i = 0
    while i < len(lvl['walls']):
        x, y, w, h = lvl['walls'][i]
        r = pygame.Rect(int(x), int(y), int(w), int(h))
        pygame.draw.rect(bg, (90, 100, 120), r)
        walls.append(r)
        i += 1
    i = 0
    while i < len(lvl['holes']):
        hx, hy, hr = lvl['holes'][i]
        pygame.draw.circle(bg, (10, 10, 10), (int(hx), int(hy)), int(hr))
        i += 1
    gx, gy, gr = lvl['goal']
    pygame.draw.circle(bg, (240, 200, 60), (int(gx), int(gy)), int(gr), 2)
    return bg, walls

def marble_rect(cx, cy):
    r = level.MARBLE_RADIUS
    return pygame.Rect(int(cx - r), int(cy - r), r * 2, r * 2)

def rect_hits_screen(rect):
    return rect.left < 0 or rect.right > W or rect.top < 0 or rect.bottom > H

def rect_hits_wall(rect, walls):
    i = 0
    while i < len(walls):
        if rect.colliderect(walls[i]):
            return 1
        i += 1
    return 0

def resolve_wall_overlap(px, py, walls):
    guard = 0
    while guard < 8:
        ball = marble_rect(px, py)
        if not rect_hits_wall(ball, walls):
            break

        best_wall = None
        best_pen = None
        best_side = 'left'

        i = 0
        while i < len(walls):
            wall = walls[i]
            if ball.colliderect(wall):
                left_pen = ball.right - wall.left
                right_pen = wall.right - ball.left
                top_pen = ball.bottom - wall.top
                bottom_pen = wall.bottom - ball.top

                side = 'left'
                pen = left_pen
                if right_pen < pen:
                    side = 'right'
                    pen = right_pen
                if top_pen < pen:
                    side = 'top'
                    pen = top_pen
                if bottom_pen < pen:
                    side = 'bottom'
                    pen = bottom_pen

                if best_pen is None or pen < best_pen:
                    best_pen = pen
                    best_wall = wall
                    best_side = side
            i += 1

        if best_wall is None:
            break

        if best_side == 'left':
            px = best_wall.left - level.MARBLE_RADIUS
        elif best_side == 'right':
            px = best_wall.right + level.MARBLE_RADIUS
        elif best_side == 'top':
            py = best_wall.top - level.MARBLE_RADIUS
        else:
            py = best_wall.bottom + level.MARBLE_RADIUS

        guard += 1

    return px, py

def main():
    if len(sys.argv) < 2:
        sys.stderr.write('usage: python2.5 game.py <level.lvl> [tilt_source] [telemetry_csv] [timeout_s]\n')
        return 2
    level_path = sys.argv[1]
    if len(sys.argv) > 2:
        tilt_path = sys.argv[2]
    else:
        tilt_path = ACCEL
    if len(sys.argv) > 4:
        timeout_s = float(sys.argv[4])
    else:
        timeout_s = 60.0

    lvl = level.load(level_path)
    errors = level.validate(lvl)
    if errors:
        i = 0
        while i < len(errors):
            sys.stdout.write(errors[i] + '\n')
            i += 1
        return 2

    telemetry_path = sys.argv[3] if len(sys.argv) > 3 else default_telemetry_path(level_path, lvl)

    pygame.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN, 16)
    bg, walls = build_background(lvl)
    tx = Telemetry(telemetry_path)

    px, py = lvl['start']
    spawn_x, spawn_y = px, py
    vx = 0.0
    vy = 0.0

    last_tilt = (0, 0, -1000)
    t0 = time.time()
    last_frame_t = t0
    last_sample = t0
    last_second = t0

    sec_frames = 0
    frames = 0
    deaths = 0
    outcome = ''
    pending_event = ''

    calibration_sum_x = 0.0
    calibration_sum_y = 0.0
    calibration_count = 0
    calibrated = 0
    level_x = 0.0
    level_y = 0.0
    tilt_history = []

    vibrate_until = 0.0
    vibrator_on = 0

    try:
        while not outcome:
            frame_now = time.time()
            if frame_now - t0 >= timeout_s:
                outcome = 'timeout'
                break

            vibrator_on = update_vibrator(frame_now, vibrate_until, vibrator_on)

            for e in pygame.event.get():
                if e.type == pygame.QUIT or e.type == pygame.KEYDOWN or e.type == pygame.MOUSEBUTTONDOWN:
                    outcome = 'quit'
                    break
            if outcome:
                break

            dt = frame_now - last_frame_t
            if dt < 0.0:
                dt = 0.0
            if dt > 0.05:
                dt = 0.05
            last_frame_t = frame_now

            last_tilt = read_tilt(tilt_path, last_tilt)
            raw_x, raw_y, raw_z = last_tilt

            if not calibrated:
                calibration_sum_x += raw_x
                calibration_sum_y += raw_y
                calibration_count += 1
                if frame_now - t0 >= CALIBRATION_WINDOW and calibration_count > 0:
                    level_x = calibration_sum_x / calibration_count
                    level_y = calibration_sum_y / calibration_count
                    calibrated = 1
                    tilt_history = []
                screen_ax = 0.0
                screen_ay = 0.0
            else:
                adj_x = raw_x - level_x
                adj_y = raw_y - level_y
                tilt_history.append((adj_x, adj_y))
                if len(tilt_history) > 3:
                    del tilt_history[0]

                sum_x = 0.0
                sum_y = 0.0
                i = 0
                while i < len(tilt_history):
                    sum_x += tilt_history[i][0]
                    sum_y += tilt_history[i][1]
                    i += 1

                tilt_x = apply_dead_zone(sum_x / len(tilt_history))
                tilt_y = apply_dead_zone(sum_y / len(tilt_history))
                screen_ax = -tilt_x
                screen_ay = -tilt_y

            if calibrated:
                vx += screen_ax * ACCEL_PER_MG * dt
                vy += screen_ay * ACCEL_PER_MG * dt

                drag = 1.0 - DRAG * dt
                if drag < 0.0:
                    drag = 0.0
                vx *= drag
                vy *= drag

                speed_sq = vx * vx + vy * vy
                max_speed_sq = MAX_SPEED * MAX_SPEED
                if speed_sq > max_speed_sq:
                    speed = math.sqrt(speed_sq)
                    if speed > 0.0:
                        scale = MAX_SPEED / speed
                        vx *= scale
                        vy *= scale

                nx = px + vx * dt
                ny = py + vy * dt

                wall_buzz_ms = 0

                test_x = marble_rect(nx, py)
                if rect_hits_screen(test_x) or rect_hits_wall(test_x, walls):
                    impact = vx
                    if impact < 0.0:
                        impact = -impact
                    buzz_ms = wall_buzz_duration(impact)
                    if buzz_ms > wall_buzz_ms:
                        wall_buzz_ms = buzz_ms
                    nx = px
                    vx = -vx * RESTITUTION

                test_y = marble_rect(nx, ny)
                if rect_hits_screen(test_y) or rect_hits_wall(test_y, walls):
                    impact = vy
                    if impact < 0.0:
                        impact = -impact
                    buzz_ms = wall_buzz_duration(impact)
                    if buzz_ms > wall_buzz_ms:
                        wall_buzz_ms = buzz_ms
                    ny = py
                    vy = -vy * RESTITUTION

                px, py = nx, ny
                px, py = resolve_wall_overlap(px, py, walls)

                if wall_buzz_ms > 0:
                    vibrate_until, vibrator_on = buzz_vibrator(frame_now, wall_buzz_ms, vibrate_until, vibrator_on)
                    if not pending_event:
                        pending_event = 'wall'

            hit = hole_hit(px, py, lvl['holes'])
            if hit >= 0:
                pending_event = 'hole'
                deaths += 1
                vibrate_until, vibrator_on = buzz_vibrator(frame_now, 250, vibrate_until, vibrator_on)
                px, py = spawn_x, spawn_y
                vx = 0.0
                vy = 0.0

            gx, gy, gr = lvl['goal']
            dx = px - gx
            dy = py - gy
            if dx * dx + dy * dy <= gr * gr:
                outcome = 'goal'
                vibrate_until, vibrator_on = buzz_vibrator(frame_now, 120, vibrate_until, vibrator_on)

            screen.blit(bg, (0, 0))
            pygame.draw.circle(screen, (240, 240, 240), (int(px), int(py)), level.MARBLE_RADIUS)
            pygame.display.flip()

            frames += 1
            sec_frames += 1

            sample_now = time.time()
            if sample_now - last_sample >= 0.1:
                tx.sample(sample_now - t0, px, py, vx, vy, raw_x, raw_y, pending_event)
                pending_event = ''
                last_sample = sample_now
            if sample_now - last_second >= 1.0:
                tx.second(sample_now - t0, sec_frames / (sample_now - last_second))
                sec_frames = 0
                last_second = sample_now

            if outcome == 'goal':
                tx.sample(sample_now - t0, px, py, vx, vy, raw_x, raw_y, 'goal')

        elapsed = time.time() - t0
        avg_fps = frames / elapsed if elapsed > 0.0 else 0.0
        if not outcome:
            outcome = 'timeout'

        tx.close({'outcome': outcome, 'elapsed': elapsed, 'deaths': deaths, 'par': lvl['par'],
                  'frames': frames, 'avg_fps': avg_fps})
        pygame.quit()
        sys.stdout.write('RESULT outcome=%s elapsed=%.1f deaths=%d par=%g frames=%d avg_fps=%.1f\n' % (
            outcome, elapsed, deaths, lvl['par'], frames, avg_fps))
        sys.stdout.flush()
        if outcome == 'goal':
            return 0
        if outcome == 'quit':
            return 1
        if outcome == 'timeout':
            return 3
        return 1
    finally:
        write_vibrator('0')

if __name__ == '__main__':
    sys.exit(main())
