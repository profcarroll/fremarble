# marble_fps.py -- frame-rate measurement for a tilt-driven marble on the N900.
# Python 2.5 / pygame 1.9.1.  No fonts, no images: just what the game loop must do.
#
#   python2.5 marble_fps.py [seconds] [tilt_source]
#
# tilt_source defaults to the accelerometer sysfs file.  Hand it any other path
# (a FIFO the bot writes "x y z\n" lines into) and nothing else changes: that is
# the seam the headless player will use.
import os, sys, time
import pygame

ACCEL = '/sys/class/i2c-adapter/i2c-3/3-001d/coord'
W, H = 800, 480
SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
SRC = sys.argv[2] if len(sys.argv) > 2 else ACCEL
LOG = '/home/user/MyDocs/marble_fps.csv'

def read_tilt():
    # The N900 accelerometer reports milli-g on three axes; ~ -918 on z at rest.
    try:
        f = open(SRC); s = f.read(); f.close()
        x, y, z = [int(v) for v in s.split()[:3]]
        return x, y, z
    except Exception:
        return 0, 0, -1000

pygame.init()
pygame.mouse.set_visible(False)
screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN, 16)
bg = pygame.Surface((W, H)); bg.fill((20, 24, 30))
walls = [pygame.Rect(200, 100, 24, 280), pygame.Rect(400, 0, 24, 200),
         pygame.Rect(400, 320, 24, 160), pygame.Rect(600, 140, 24, 220)]
for w in walls:
    pygame.draw.rect(bg, (90, 100, 120), w)
R = 18
px, py = 60.0, H / 2.0
vx = vy = 0.0
GAIN, FRICTION = 0.0025, 0.985

log = open(LOG, 'w'); log.write('t,fps,x,y,z,accel_read_ms\n')
t0 = time.time(); last = t0; frames = 0; sec_frames = 0; sec_start = t0
worst = 9999.0; totals = 0
running = True
while running and time.time() - t0 < SECONDS:
    for e in pygame.event.get():
        if e.type == pygame.QUIT or e.type == pygame.KEYDOWN or e.type == pygame.MOUSEBUTTONDOWN:
            running = False
    a0 = time.time(); ax, ay, az = read_tilt(); aread = (time.time() - a0) * 1000.0
    # Landscape N900: device x axis maps to screen y, y axis to screen x (sign found by trying).
    vx += -ay * GAIN; vy += -ax * GAIN
    vx *= FRICTION; vy *= FRICTION
    nx, ny = px + vx, py + vy
    ball = pygame.Rect(int(nx - R), int(ny - R), 2 * R, 2 * R)
    if nx - R < 0 or nx + R > W: vx = -vx * 0.6; nx = px
    if ny - R < 0 or ny + R > H: vy = -vy * 0.6; ny = py
    for w in walls:
        if ball.colliderect(w):
            if abs(vx) > abs(vy): vx = -vx * 0.6; nx = px
            else: vy = -vy * 0.6; ny = py
    px, py = nx, ny
    screen.blit(bg, (0, 0))
    pygame.draw.circle(screen, (240, 200, 60), (int(px), int(py)), R)
    pygame.display.flip()
    frames += 1; sec_frames += 1; totals += 1
    now = time.time()
    if now - sec_start >= 1.0:
        fps = sec_frames / (now - sec_start)
        if fps < worst: worst = fps
        log.write('%.1f,%.1f,%d,%d,%d,%.2f\n' % (now - t0, fps, ax, ay, az, aread))
        sec_frames = 0; sec_start = now
elapsed = time.time() - t0
log.close(); pygame.quit()
print 'frames=%d elapsed=%.1fs avg_fps=%.1f worst_second_fps=%.1f log=%s' % (
    frames, elapsed, frames / elapsed, worst, LOG)
