=== FILE: game.py
```python
import os, re, sys, time
import pygame
import level
from telemetry import Telemetry

ACCEL = '/sys/class/i2c-adapter/i2c-3/3-001d/coord'
GAIN = 0.0025
FRICTION = 0.985
W = level.SCREEN_W
H = level.SCREEN_H

def hole_hit(px, py, r, holes):
    """Return the first overlapping hole index.
    Holes are checked in order from left to right in the list.
    Return -1 when the marble does not overlap any hole.
    """
    i = 0
    rr = r * r
    while i < len(holes):
        hx, hy, hr = holes[i]
        dx = px - hx
        dy = py - hy
        sr = r + hr
        if dx * dx + dy * dy <= sr * sr:
            return i
        i += 1
    return -1

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

def main():
    if len(sys.argv) < 2:
        sys.stderr.write('usage: python2.5 game.py <level.lvl> [tilt_source] [telemetry_csv] [timeout_s]\n')
        return 2
    level_path = sys.argv[1]
    tilt_path = sys.argv[2] if len(sys.argv) > 2 else ACCEL
    timeout_s = float(sys.argv[4]) if len(sys.argv) > 4 else 60.0
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
    vx = vy = 0.0
    ax = ay = az = 0
    last_tilt = (0, 0, -1000)
    t0 = time.time()
    last_sample = t0
    last_second = t0
    sec_frames = 0
    frames = 0
    deaths = 0
    outcome = ''
    pending_event = ''

    while not outcome:
        now = time.time()
        if now - t0 >= timeout_s:
            outcome = 'timeout'
            break
        for e in pygame.event.get():
            if e.type == pygame.QUIT or e.type == pygame.KEYDOWN or e.type == pygame.MOUSEBUTTONDOWN:
                outcome = 'quit'
                break
        if outcome:
            break

        last_tilt = read_tilt(tilt_path, last_tilt)
        ax, ay, az = last_tilt
        vx += -ay * GAIN
        vy += -ax * GAIN
        vx *= FRICTION
        vy *= FRICTION

        nx = px + vx
        ny = py + vy
        ball = pygame.Rect(int(nx - level.MARBLE_RADIUS), int(ny - level.MARBLE_RADIUS),
                           level.MARBLE_RADIUS * 2, level.MARBLE_RADIUS * 2)

        if nx - level.MARBLE_RADIUS < 0 or nx + level.MARBLE_RADIUS > W:
            vx = -vx * 0.6
            nx = px
        if ny - level.MARBLE_RADIUS < 0 or ny + level.MARBLE_RADIUS > H:
            vy = -vy * 0.6
            ny = py
        i = 0
        while i < len(walls):
            if ball.colliderect(walls[i]):
                if abs(vx) > abs(vy):
                    vx = -vx * 0.6
                    nx = px
                else:
                    vy = -vy * 0.6
                    ny = py
            i += 1

        px, py = nx, ny
        hit = hole_hit(px, py, level.MARBLE_RADIUS, lvl['holes'])
        if hit >= 0:
            pending_event = 'hole'
            deaths += 1
            px, py = spawn_x, spawn_y
            vx = vy = 0.0
        gx, gy, gr = lvl['goal']
        dx = px - gx
        dy = py - gy
        if dx * dx + dy * dy <= gr * gr:
            outcome = 'goal'

        screen.blit(bg, (0, 0))
        pygame.draw.circle(screen, (240, 240, 240), (int(px), int(py)), level.MARBLE_RADIUS)
        pygame.display.flip()

        frames += 1
        sec_frames += 1
        now = time.time()
        if now - last_sample >= 0.1:
            tx.sample(now - t0, px, py, vx, vy, ax, ay, pending_event)
            pending_event = ''
            last_sample = now
        if now - last_second >= 1.0:
            tx.second(now - t0, sec_frames / (now - last_second))
            sec_frames = 0
            last_second = now

        if outcome == 'goal':
            tx.sample(now - t0, px, py, vx, vy, ax, ay, 'goal')

    elapsed = time.time() - t0
    avg_fps = frames / elapsed if elapsed > 0.0 else 0.0
    if outcome == 'quit' or outcome == 'timeout' or outcome == 'goal':
        pass
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

if __name__ == '__main__':
    sys.exit(main())
```

=== FILE: telemetry.py
```python
import csv
import os

class Telemetry(object):
    def __init__(self, path):
        self.path = path
        self.f = None
        self.w = None
        self.open()

    def open(self):
        if self.f:
            return
        d = os.path.dirname(self.path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        self.f = open(self.path, 'w')
        self.w = csv.writer(self.f)
        self.w.writerow(['t', 'x', 'y', 'vx', 'vy', 'ax', 'ay', 'event'])
        self.f.flush()

    def _write(self, row):
        self.w.writerow(row)
        self.f.flush()

    def sample(self, t, x, y, vx, vy, ax, ay, event):
        self._write([t, x, y, vx, vy, ax, ay, event])

    def second(self, t, fps):
        self._write([t, fps, '', '', '', '', '', 'fps'])

    def close(self, summary_dict):
        if not self.f:
            return
        items = summary_dict.items()
        items.sort()
        s = []
        i = 0
        while i < len(items):
            k, v = items[i]
            s.append(str(k) + '=' + str(v))
            i += 1
        self._write(['', ';'.join(s), '', '', '', '', '', 'summary'])
        self.f.close()
        self.f = None
        self.w = None
```

=== FILE: bot_tilt.py
```python
import sys
import time

def parse_script(script):
    parts = script.split(';')
    out = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if part:
            xyz, secs = part.split(':', 1)
            x, y, z = xyz.split(',', 2)
            out.append((int(x), int(y), int(z), float(secs)))
        i += 1
    return out

def write_tilt(path, x, y, z):
    f = open(path, 'w')
    try:
        f.write('%d %d %d\n' % (x, y, z))
        f.flush()
    finally:
        f.close()

def main():
    if len(sys.argv) < 3:
        sys.stderr.write('usage: python2.5 bot_tilt.py <tilt_file> <script>\n')
        return 2
    path = sys.argv[1]
    script = parse_script(sys.argv[2])
    i = 0
    while i < len(script):
        x, y, z, secs = script[i]
        end = time.time() + secs
        while time.time() < end:
            write_tilt(path, x, y, z)
            time.sleep(0.1)
        i += 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
```


real	1m2.589s
user	0m10.384s
sys	0m2.307s
