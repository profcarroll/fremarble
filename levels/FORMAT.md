# Tilt Levels file format (.lvl)

Plain text, one directive per line. No JSON, no nesting. Parsed with
`str.split()` only. Blank lines and lines starting with `#` are ignored.
Screen is 800x480 px, origin (0,0) at top-left. Marble radius is a fixed
game constant (18 px), not stored per level.

Directives (all values are numbers unless noted):

    NAME <text>              rest of line is the level's display name
    PAR <seconds>            target completion time
    START <x> <y>            marble spawn point (once)
    GOAL <x> <y> <radius>    goal circle (once)
    WALL <x> <y> <w> <h>     one axis-aligned wall rect (repeatable)
    HOLE <x> <y> <radius>    one deadly hole circle (repeatable)

x,y for WALL is its top-left corner. Order of directives does not matter.
Unknown directives are ignored (forward compatible).

## Worked example

    NAME Corner Test
    PAR 15
    START 60 60
    GOAL 700 400 20
    WALL 0 0 800 40
    WALL 0 200 800 40
    HOLE 650 220 18

This describes a short corridor between two horizontal walls (y 40-200),
a hole near the goal, and a 15 second par time.
