# test_level.py - load and validate every level, check pack ordering.
# Python 2.5 safe: no print(), plain string ops only.

import level

LEVELS_DIR = 'levels'


def main():
    ok = 1

    paths = level.find_levels(LEVELS_DIR)
    if not paths:
        print 'FAIL: no .lvl files under %s' % LEVELS_DIR
        return

    for path in paths:
        lvl = level.load(path)
        errors = level.validate(lvl)
        if errors:
            ok = 0
            print 'FAIL: %s' % path
            for e in errors:
                print '  - %s' % e
        else:
            print 'PASS: %s (%s)' % (path, lvl['name'])

    # A directory is the whole pack in filename order; a single file is just
    # that one level (so the bot and telemetry probes stay scoped to one level).
    if len(paths) > 1:
        if paths != sorted(paths):
            ok = 0
            print 'FAIL: pack is not in filename order'
        one = level.find_levels(paths[0])
        if one != [paths[0]]:
            ok = 0
            print 'FAIL: a single file should play only itself, got %s' % one

    if ok:
        print 'ALL PASS: %d level(s)' % len(paths)


if __name__ == '__main__':
    main()
