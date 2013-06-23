#! /usr/bin/env python3
"""Run any doctests in this package
"""

import doctest
import os
import sys

THIS_DIR = os.path.split(__file__)[0]

def main():
    total_tests = 0
    total_failures = 0
    for dirpath, dirnames, filenames in os.walk(THIS_DIR):
        for name in filenames:
            base, ext = os.path.splitext(name)
            if ext != '.py':
                continue
            path = os.path.join(dirpath, base)
            relpath = os.path.relpath(path, THIS_DIR)
            words = relpath.split(os.sep)
            module = '.'.join(words)

            environment = {}
            try:
                exec('import %s; thing=%s'%(module, module), environment)
            except AttributeError:
                pass
            except ImportError as e:
                print('ImportError: %s'%e)
                break

            failures, tests = doctest.testmod(environment['thing'])

            if tests:
                testword = "test"
                if tests != 1: testword = "tests"
                failword = "failure"
                if failures != 1: failword = "failures"
                print()
                print("File %s: %d %s, %d %s"%(path,
                        tests,'test' if tests==1 else 'tests',
                        failures, 'failure' if failures==1 else 'failures'))
                print()
                total_tests += tests
                total_failures += failures
    print('Found %d %s, %d %s'%(total_tests, 'test' if total_tests==1 else 'tests',
            total_failures, 'failure' if total_failures==1 else 'failures'))
    return total_failures

if __name__ == "__main__":
    failed = main()
    if failed:
        sys.exit(1)
