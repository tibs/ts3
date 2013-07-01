#! /usr/bin/env python3
"""Run the doctest on a text file

    Usage: doctext.py  [file]

[file] defaults to ``test.txt``
"""

import sys
import doctest

def main():
    args = sys.argv[1:]
    filename = None
    verbose = False

    for word in args:
        if word in ("-v", "-verbose"):
            verbose = True
        elif word in ("-h", "-help", "/?", "/help", "--help"):
            print(__doc__)
            return
        else:
            if filename:
                print("Filename {!r} already specified".format(filename))
                return
            else:
                filename = word

    if not filename:
        filename = "test.txt"

    (failures,tests) = doctest.testfile(filename,verbose=verbose)

    testword = "test"
    if tests != 1: testword = "tests"
    failword = "failure"
    if failures != 1: failword = "failures"
    print()
    print("File {}: {} {}, {} {}".format(filename,tests,testword,failures,failword))
    print()
    if failures == 0:
        print('The little light is GREEN')
    else:
        print('The little light is RED')

if __name__ == "__main__":
    main()
