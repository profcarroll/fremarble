import sys, os, glob
holes = [(100, 100, 20), (300, 300, 20), (650, 320, 20)]
cases = [((100, 100, 18), 0), ((330, 300, 18), 1), ((339, 300, 18), -1), ((338, 300, 18), 1), ((500, 50, 18), -1), ((640, 330, 18), 2)]
for path in sorted(glob.glob(os.path.join(os.path.dirname(sys.argv[0]), '*.py'))):
    name = os.path.basename(path)[:-3]
    if name == 'run': continue
    try:
        ns = {}
        execfile(path, ns)
        fn = ns['hole_hit']
        bad = [(args, want, fn(args[0], args[1], args[2], holes)) for args, want in cases if fn(args[0], args[1], args[2], holes) != want]
        print '%-22s %s %s' % (name, bad and 'FAIL' or 'PASS', bad)
    except Exception, e:
        print '%-22s ERROR %s' % (name, e)
