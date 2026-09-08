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
READY_PAUSE = 0.6
COMPLETE_HOLD = 4.0
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

def level_telemetry_path(explicit, level_path, lvl):
    """Derive a per-level telemetry path from an explicit base path, so the
    levels in a pack do not all write over one file. telemetry/run.csv plus a
    level named 'Switchback' becomes telemetry/run-switchback.csv."""
    d = os.path.dirname(explicit)
    stem, ext = os.path.splitext(os.path.basename(explicit))
    if not ext:
        ext = '.csv'
    base = lvl.get('name', '')
    if not base:
        base = os.path.splitext(os.path.basename(level_path))[0]
    name = stem + '-' + sanitize_name(base) + ext
    if d:
        return os.path.join(d, name)
    return name

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

def play_level(screen, lvl, tilt_path, telemetry_path, timeout_s, session, first_level):
    """Play one level to completion and return (outcome, elapsed, deaths, frames).

    outcome is 'goal', 'quit' or 'timeout'. Calibration and vibrator state live
    in the session dict and carry across levels, so the player only sets "level"
    once at the start of the pack. On the first level the half-second calibration
    is itself the get-ready pause; later levels freeze briefly (READY_PAUSE) so
    the new board can be read before it goes live.
    """
    bg, walls = build_background(lvl)
    tx = Telemetry(telemetry_path)

    px, py = lvl['start']
    spawn_x, spawn_y = px, py
    vx = 0.0
    vy = 0.0

    t0 = time.time()
    last_frame_t = t0
    last_sample = t0
    last_second = t0

    sec_frames = 0
    frames = 0
    deaths = 0
    outcome = ''
    pending_event = ''
    tilt_history = []

    if first_level:
        ready_delay = 0.0
    else:
        ready_delay = READY_PAUSE

    while not outcome:
        frame_now = time.time()
        if frame_now - t0 >= timeout_s:
            outcome = 'timeout'
            break

        session['vibrator_on'] = update_vibrator(frame_now, session['vibrate_until'], session['vibrator_on'])

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

        last_tilt = read_tilt(tilt_path, session['last_tilt'])
        session['last_tilt'] = last_tilt
        raw_x, raw_y, raw_z = last_tilt

        if not session['calibrated']:
            session['calib_sum_x'] += raw_x
            session['calib_sum_y'] += raw_y
            session['calib_count'] += 1
            if frame_now - t0 >= CALIBRATION_WINDOW and session['calib_count'] > 0:
                session['level_x'] = session['calib_sum_x'] / session['calib_count']
                session['level_y'] = session['calib_sum_y'] / session['calib_count']
                session['calibrated'] = 1
                tilt_history = []
            screen_ax = 0.0
            screen_ay = 0.0
        else:
            adj_x = raw_x - session['level_x']
            adj_y = raw_y - session['level_y']
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

        live = session['calibrated'] and (frame_now - t0) >= ready_delay

        if live:
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
                session['vibrate_until'], session['vibrator_on'] = buzz_vibrator(
                    frame_now, wall_buzz_ms, session['vibrate_until'], session['vibrator_on'])
                if not pending_event:
                    pending_event = 'wall'

            hit = hole_hit(px, py, lvl['holes'])
            if hit >= 0:
                pending_event = 'hole'
                deaths += 1
                session['vibrate_until'], session['vibrator_on'] = buzz_vibrator(
                    frame_now, 250, session['vibrate_until'], session['vibrator_on'])
                px, py = spawn_x, spawn_y
                vx = 0.0
                vy = 0.0

            gx, gy, gr = lvl['goal']
            dx = px - gx
            dy = py - gy
            if dx * dx + dy * dy <= gr * gr:
                outcome = 'goal'
                session['vibrate_until'], session['vibrator_on'] = buzz_vibrator(
                    frame_now, 120, session['vibrate_until'], session['vibrator_on'])

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
    return outcome, elapsed, deaths, frames

def new_session():
    return {
        'calibrated': 0,
        'level_x': 0.0,
        'level_y': 0.0,
        'calib_sum_x': 0.0,
        'calib_sum_y': 0.0,
        'calib_count': 0,
        'last_tilt': (0, 0, -1000),
        'vibrate_until': 0.0,
        'vibrator_on': 0,
    }

def show_complete(screen):
    """Hold a 'pack complete' screen after the last level, so finishing reads as
    a win instead of the fullscreen window vanishing like a crash. Returns on a
    tap/key or after COMPLETE_HOLD seconds."""
    write_vibrator('0')
    surf = pygame.Surface((W, H)).convert()
    surf.fill((18, 34, 24))
    cx = W // 2
    cy = H // 2
    pygame.draw.circle(surf, (240, 200, 60), (cx, cy), 60, 3)
    pygame.draw.circle(surf, (240, 240, 240), (cx, cy), level.MARBLE_RADIUS)
    try:
        pygame.font.init()
        font = pygame.font.Font(None, 64)
        label = font.render('Pack complete', True, (240, 240, 240))
        rect = label.get_rect()
        rect.center = (cx, cy - 110)
        surf.blit(label, rect)
    except Exception:
        pass
    screen.blit(surf, (0, 0))
    pygame.display.flip()
    start = time.time()
    while time.time() - start < COMPLETE_HOLD:
        stop = 0
        for e in pygame.event.get():
            if e.type == pygame.QUIT or e.type == pygame.KEYDOWN or e.type == pygame.MOUSEBUTTONDOWN:
                stop = 1
                break
        if stop:
            break
        time.sleep(0.03)

def default_levels_dir():
    """The pack played when game.py is given no level argument: the levels/
    directory next to this file, so the app-grid launcher (which passes no
    arguments) plays the whole pack regardless of the working directory."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, 'levels')

def main():
    if len(sys.argv) > 1 and sys.argv[1]:
        target = sys.argv[1]
    else:
        target = default_levels_dir()
    if len(sys.argv) > 2 and sys.argv[2]:
        tilt_path = sys.argv[2]
    else:
        tilt_path = ACCEL
    explicit_telemetry = sys.argv[3] if len(sys.argv) > 3 else ''
    if len(sys.argv) > 4:
        timeout_s = float(sys.argv[4])
    else:
        timeout_s = 60.0

    playlist = level.find_levels(target)
    if not playlist:
        sys.stderr.write('no .lvl files found at %s\n' % target)
        return 2

    # Load and validate the whole pack up front, so a bad level fails before
    # any play starts rather than halfway through the session.
    loaded = []
    i = 0
    while i < len(playlist):
        p = playlist[i]
        lvl = level.load(p)
        errors = level.validate(lvl)
        if errors:
            sys.stdout.write('FAIL %s\n' % p)
            j = 0
            while j < len(errors):
                sys.stdout.write('  ' + errors[j] + '\n')
                j += 1
            return 2
        loaded.append((p, lvl))
        i += 1

    multi = len(loaded) > 1

    pygame.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN, 16)

    session = new_session()
    session_t0 = time.time()
    total_deaths = 0
    total_frames = 0
    cleared = 0
    session_outcome = 'complete'

    try:
        i = 0
        while i < len(loaded):
            p, lvl = loaded[i]
            if explicit_telemetry and not multi:
                telemetry_path = explicit_telemetry
            elif explicit_telemetry:
                telemetry_path = level_telemetry_path(explicit_telemetry, p, lvl)
            else:
                telemetry_path = default_telemetry_path(p, lvl)

            label = lvl.get('name', '')
            if not label:
                label = os.path.splitext(os.path.basename(p))[0]
            label = sanitize_name(label)

            outcome, elapsed, deaths, frames = play_level(
                screen, lvl, tilt_path, telemetry_path, timeout_s, session, i == 0)
            total_deaths += deaths
            total_frames += frames

            sys.stdout.write('RESULT level=%s outcome=%s elapsed=%.1f deaths=%d par=%g frames=%d avg_fps=%.1f\n' % (
                label, outcome, elapsed, deaths, lvl['par'], frames,
                frames / elapsed if elapsed > 0.0 else 0.0))
            sys.stdout.flush()

            if outcome == 'goal':
                cleared += 1
                i += 1
            else:
                session_outcome = outcome
                break

        total_elapsed = time.time() - session_t0
        avg_fps = total_frames / total_elapsed if total_elapsed > 0.0 else 0.0
        if session_outcome == 'complete':
            show_complete(screen)
        pygame.quit()
        sys.stdout.write('RESULT outcome=%s levels_cleared=%d levels=%d elapsed=%.1f deaths=%d frames=%d avg_fps=%.1f\n' % (
            session_outcome, cleared, len(loaded), total_elapsed, total_deaths, total_frames, avg_fps))
        sys.stdout.flush()
        if session_outcome == 'complete':
            return 0
        if session_outcome == 'quit':
            return 1
        if session_outcome == 'timeout':
            return 3
        return 1
    finally:
        write_vibrator('0')

if __name__ == '__main__':
    sys.exit(main())
