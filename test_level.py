# test_level.py - load and validate the example level, print PASS/FAIL.
# Python 2.5 safe: no print(), plain string ops only.

import level

LEVEL_PATH = 'levels/001-first-tilt.lvl'


def main():
    lvl = level.load(LEVEL_PATH)
    errors = level.validate(lvl)

    if errors:
        print 'FAIL: %s' % LEVEL_PATH
        for e in errors:
            print '  - %s' % e
    else:
        print 'PASS: %s (%s)' % (LEVEL_PATH, lvl['name'])


if __name__ == '__main__':
    main()
