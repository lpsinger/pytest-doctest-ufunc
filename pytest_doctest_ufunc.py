# -*- coding: utf-8 -*-

import pytest
from _pytest.doctest import _get_checker, get_optionflags, DoctestItem
from _pytest.doctest import _is_setup_py


def pytest_addoption(parser):
    help_msg = 'enable doctests that are in docstrings of Numpy ufuncs'
    parser.addoption('--doctest-ufunc', action='store_true', help=help_msg)
    parser.addini('doctest_ufunc', help_msg, default=False)


def _is_enabled(config):
    return config.getini('doctest_ufunc') or config.option.doctest_ufunc


def pytest_collect_file(path, parent):
    # Addapted from pytest.doctest
    config = parent.config
    if path.ext == ".py":
        if _is_enabled(config) and not _is_setup_py(config, path, parent):
            return DoctestModule(path, parent)


def _is_numpy_ufunc(method):
    import numpy as np
    unwrapped_method = method
    while True:
        try:
            unwrapped_method = unwrapped_method.__wrapped__
        except AttributeError:
            break
    return isinstance(unwrapped_method, np.ufunc)


class DoctestModule(pytest.Module):

    def collect(self):
        # Copied from pytest
        import doctest
        if self.fspath.basename == "conftest.py":
            module = self.config.pluginmanager._importconftest(self.fspath)
        else:
            try:
                module = self.fspath.pyimport()
            except ImportError:
                if self.config.getvalue('doctest_ignore_import_errors'):
                    pytest.skip('unable to import module %r' % self.fspath)
                else:
                    raise
        # uses internal doctest module parsing mechanism
        finder = doctest.DocTestFinder()
        optionflags = get_optionflags(self)
        runner = doctest.DebugRunner(verbose=0, optionflags=optionflags,
                                     checker=_get_checker())
        # End copied from pytest

        for method in module.__dict__.values():
            if _is_numpy_ufunc(method):
                for test in finder.find(method, module=module):
                    if test.examples:  # skip empty doctests
                        yield DoctestItem(test.name, self, runner, test)
