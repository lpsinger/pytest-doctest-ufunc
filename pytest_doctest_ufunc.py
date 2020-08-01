# -*- coding: utf-8 -*-

from packaging.version import Version
import pytest
from _pytest.doctest import _get_checker, get_optionflags, DoctestItem

# Copied from pytest-doctestplus
PYTEST_GT_5 = Version(pytest.__version__) > Version('5.9.9')


def pytest_addoption(parser):
    help_msg = 'enable doctests that are in docstrings of Numpy ufuncs'
    parser.addoption('--doctest-ufunc', action='store_true', help=help_msg)
    parser.addini('doctest_ufunc', help_msg, default=False)


# Copied from pytest.doctest
def _is_setup_py(path):
    if path.basename != "setup.py":
        return False
    contents = path.read_binary()
    return b"setuptools" in contents or b"distutils" in contents


def _is_enabled(config):
    return config.getini('doctest_ufunc') or config.option.doctest_ufunc


def pytest_collect_file(path, parent):
    # Addapted from pytest.doctest
    config = parent.config
    if path.ext == ".py":
        if _is_enabled(config) and not _is_setup_py(path):
            return DoctestModule.from_parent(parent, fspath=path)


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
        # Adapted from pytest
        import doctest
        if self.fspath.basename == "conftest.py":
            # Copied from pytest-doctestplus
            if PYTEST_GT_5:
                module = self.config.pluginmanager._importconftest(
                    self.fspath, self.config.getoption("importmode"))
            else:
                module = self.config.pluginmanager._importconftest(
                    self.fspath)
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
                        yield DoctestItem.from_parent(
                            self, name=test.name, runner=runner, dtest=test)
