import collections
import importlib
import os
import re
import sys


TEST_MODULE = re.compile(r'tests\.((?:\w+\.)*)test_(\w+)')
PYTHON_FILE = re.compile(r'(.*)\.py')
FIDDLE_WITH_COVERAGE = False


def get_module_names_under(path):
    for entry in os.listdir(path):
        if os.path.isdir(os.path.join(path, entry)):
            if os.path.exists(os.path.join(path, entry, '__init__.py')):
                yield entry
        else:
            match = PYTHON_FILE.fullmatch(entry)
            if match:
                yield entry.group(1)


class DivideAndCoverConfig(collections.namedtuple(
        'DivideAndCoverConfig', 'auto_detect modules')):

    @classmethod
    def from_dict(cls, dct):
        dct = dict(dct)
        config = cls(auto_detect=dct.pop('auto_detect', True),
                     modules=dct.pop('modules', ()))
        for key in sorted(dct):
            print('Unexpected Divide and Cover config key: {}'.format(key))
        return config


def module_path(test_module_path, test_module):
    config = DivideAndCoverConfig.from_dict(
        getattr(test_module, 'DIVIDE_AND_COVER_CONFIG', {}))
    if config.auto_detect:
        match = TEST_MODULE.fullmatch(test_module_path)
        if match:
            yield ''.join(match.groups())
    for module in config.modules:
        yield module


def pytest_addoption(parser):
    parser.addoption('--divide-and-cover', action='store_true',
                     help='activate divide and cover tracing')


def pytest_configure(config):
    if config.option.divide_and_cover:
        from divide_and_cover.coverage_handler import UNDER_WRAPPER
        if UNDER_WRAPPER:
            global FIDDLE_WITH_COVERAGE
            FIDDLE_WITH_COVERAGE = True
        else:
            print('Warning: called with --divide-and-cover, but not running '
                  'under divide_and_cover. Not activating plugin.')


# This is probably wrong
def pytest_collection_modifyitems(session, config, items):
    if FIDDLE_WITH_COVERAGE:
        from divide_and_cover.coverage_handler import coverage_script
        modules = sys.modules.copy()
        paths = []
        for test_path, module in modules.items():
            module_paths = []
            for module_path_ in module_path(test_path, module):
                paths.append(module_path_)
                module_paths.append(module_path_)
            coverage_script.new_coverage(test_path, module_paths)
        # This next bit needs to be run under a coverage tracer, with source
        # based on paths. Specifically, it should use the root package from
        # each path
        roots = sorted({path.split('.', 1)[0] for path in paths})
        coverage_script.make_import_coverage(roots)
        print('Covering packages under: {}'.format(roots))
        coverage_script.switch_coverage(coverage_script.import_coverage)
        try:
            for path in paths:
                try:
                    importlib.import_module(path)
                except ImportError:
                    print('Could not import {}'.format(path))
        finally:
            coverage_script.deactivate_coverage()


def pytest_runtest_setup(item):
    if FIDDLE_WITH_COVERAGE:
        from divide_and_cover.coverage_handler import coverage_script
        coverage_script.activate_coverage(item.obj.__module__)


def pytest_runtest_teardown(item, nextitem):
    if FIDDLE_WITH_COVERAGE:
        from divide_and_cover.coverage_handler import coverage_script
        coverage_script.deactivate_coverage()
