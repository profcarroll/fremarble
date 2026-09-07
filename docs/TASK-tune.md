TASK-tune: make the marble feel like a marble. Evidence from the first human play-test
(telemetry/human1.csv, 120 s, 7 deaths, goal never reached; a scripted bot clears the same
level in 10 s):
  - peak speed 28.9 px/frame (~3,000 px/s on an 800 px screen); mean tilt 232 mg, peaks 1,000 mg
  - 267 velocity reversals in 120 s: the marble ping-pongs between walls
  - three deaths within 1.6 s (respawn, rush, die); hole kills on touch
  - last 40 s parked in a corner at rest tilt (18, -36 mg): no dead zone, no calibration
  - frame rate wandered 82..124 fps and physics are per-frame, so feel changes with fps
  - accelerometer noise at rest: +/-36 mg on x and y, occasional single-sample outliers

Change game.py only. Keep arguments, telemetry calls, RESULT line and exit codes identical.
1. Time-based physics. Measure dt each frame (clamp to 0.05 s). Units: px, s, mg.
   accel_px_s2 = tilt_mg * ACCEL_PER_MG with ACCEL_PER_MG = 1.2   (600 mg -> 720 px/s^2:
   from rest, the 600 px corridor takes ~1.3 s; 200 mg -> 240 px/s^2, ~2.2 s).
   v += a*dt ; rolling drag: v *= max(0, 1 - DRAG*dt) with DRAG = 0.8 per second;
   clamp speed to MAX_SPEED = 900 px/s ; x += v*dt. Keep the axis mapping:
   screen_ax = -ay_mg, screen_ay = -ax_mg.
2. Calibration and filtering. Average the first 0.5 s of tilt after start as "level" and
   subtract it (a hand holds the device at an angle; that angle should mean rest). A bot file
   writing "0 0 -1000" therefore stays level. Dead zone: |tilt| < 40 mg -> 0. Low-pass: use
   the mean of the last 3 samples.
3. Walls: restitution 0.3 (not 0.6). Screen edges the same. When a bounce happens with
   impact speed > 150 px/s, buzz the vibrator for 40 ms; > 400 px/s, 80 ms.
4. Holes: capture when the marble CENTER is inside the hole circle (dist < hole radius), not
   on touch. On capture: buzz 250 ms, then respawn as now.
5. Goal unchanged (center within goal radius). Buzz 120 ms on goal.
6. Haptics, non-blocking: write '255' to /sys/class/leds/twl4030:vibrator/brightness to start
   and '0' to stop; keep a "vibrate_until" timestamp and write '0' once time passes it.
   Wrap every write in try/except; if the file is absent (laptop, bot host) do nothing.
   Always write '0' on exit.
7. Telemetry: unchanged calls; add event 'wall' on bounces that buzz (only when no other
   event is pending that sample).
Bootstrap rules still apply: Python 2.5 (no with, no print(), no str.format, no json,
no 'except X as e', no comprehensions), pygame only, no threads.
Output the complete game.py as a fenced block preceded by '=== FILE: game.py'. Nothing else.
