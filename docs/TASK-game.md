Write the playable game loop for "Tilt Levels" on the N900. Deliverables, Python 2.5-safe:

1. game.py — usage: python2.5 game.py <level.lvl> [tilt_source] [telemetry_csv] [timeout_s]
   - Loads the level with level.load(); if level.validate() returns errors, print them and exit 2.
   - tilt_source defaults to /sys/class/i2c-adapter/i2c-3/3-001d/coord. Read it EVERY FRAME
     with open/read/close (it may be a plain file rewritten by a bot); parse three ints
     "x y z" (milli-g); on any read error keep the last tilt. Mapping (already proven):
     vx += -ay * GAIN ; vy += -ax * GAIN ; GAIN = 0.0025 ; FRICTION = 0.985 per frame.
   - Fullscreen 800x480, 16 bit, mouse hidden. Draw once into a background surface:
     walls (rect fill), holes (dark filled circle), goal (ring). Each frame: blit background,
     draw marble (radius level.MARBLE_RADIUS), flip. No fonts; do not import pygame.font.
   - Physics: move by (vx, vy); bounce off screen edges and off any wall rect with 0.6
     restitution, the same pre-move test as the reference loop below. Hole: use hole_hit()
     below; on hit -> event 'hole', deaths += 1, respawn at start with zero velocity.
     Goal: marble center within goal radius -> event 'goal', outcome 'goal', exit 0.
   - Exit conditions: any key or touch -> outcome 'quit' (exit 1); timeout_s (default 60)
     -> outcome 'timeout' (exit 3).
   - Last line printed on stdout, always:
     RESULT outcome=<goal|quit|timeout> elapsed=<s> deaths=<n> par=<s> frames=<n> avg_fps=<f>
2. telemetry.py — class Telemetry(path): open(); sample(t, x, y, vx, vy, ax, ay, event);
   second(t, fps); close(summary_dict). Writes CSV: header
   "t,x,y,vx,vy,ax,ay,event"; sample() is called at most 10 times per second (the game
   decides), second() writes a row with event 'fps' and fps in the x column; close() writes
   a final row with event 'summary' and the summary as key=value pairs joined by ';' in the
   x column. Flush after every write (the run may be killed).
   Default path if game.py is given none: telemetry/<levelname-lowercased-dashes>-<int time>.csv,
   creating the directory if needed.
3. bot_tilt.py — usage: python2.5 bot_tilt.py <tilt_file> <script>; script is a string like
   "0,-600,-800:2.5;500,0,-800:1.5" meaning write "0 -600 -800" for 2.5 s, then the next;
   rewrite the file every 0.1 s (time.sleep(0.1) is fine in Python); exit when done.

Keep each file under 150 lines. No classes except Telemetry. Output every deliverable as a
fenced code block preceded by a line '=== FILE: <relative path>'. Nothing else.
