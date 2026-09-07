Design the level file format for "Tilt Levels", a Marble Madness-style tilt game on the
N900 (800x480, marble radius 18 px). A level needs: a name, a start point, a goal, walls
(axis-aligned rectangles), holes (circles that kill), and a par time in seconds.
Deliverables, all Python 2.5-safe per .github/copilot-instructions.md:
1. levels/FORMAT.md - the format, in under 40 lines, with one worked example.
2. levels/001-first-tilt.lvl - one hand-designed level that is solvable and takes a
   beginner about 20 seconds: a corridor with two turns and one hole near the goal.
3. level.py - load(path) -> dict, and validate(level) -> list of error strings
   (start/goal inside the screen, not inside a wall, marble fits between walls).
4. test_level.py - a script that loads and validates the example and prints PASS/FAIL.
Do not use the json module; the file format must be parseable with plain string ops.
