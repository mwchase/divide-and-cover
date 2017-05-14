#!/usr/bin/env python3

import sys

import coverage_handler


coverage_handler.UNDER_WRAPPER = True

try:
    coverage_handler.coverage_script.command_line(sys.argv[1:])
finally:
    coverage_handler.coverage_script.complete()
