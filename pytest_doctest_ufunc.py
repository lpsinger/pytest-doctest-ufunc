# -*- coding: utf-8 -*-

from packaging.version import Version
import pytest
from _pytest.doctest import _get_checker, get_optionflags, DoctestItem

# Copied from pytest-doctestplus
_pytest_version = Version(pytest.__version__)
PYTEST_GT_5 = _pytest_version > Version('5.9.9')
PYTEST_GE_7_0 = any([_pytest_version.is_devrelease,
                     _pytest_version.is_prerelease,
                     _pytest_version >= Version('7.0')])


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
        # When running directly from pytest we need to make sure that we
        # don't accidentally import setup.py!
        if PYTEST_GE_7_0:
            fspath = self.path
            filepath = self.path.name
        else:
            fspath = self.fspath
            filepath = self.fspath.basename

        if filepath == "setup.py":
            return
        elif filepath == "conftest.py":
            if PYTEST_GE_7_0:
                module = self.config.pluginmanager._importconftest(
                    self.path, self.config.getoption("importmode"),
                    rootpath=self.config.rootpath)
            elif PYTEST_GT_5:
                module = self.config.pluginmanager._importconftest(
                    self.fspath, self.config.getoption("importmode"))
            else:
                module = self.config.pluginmanager._importconftest(
                    self.fspath)
        else:
            try:
                if PYTEST_GT_5:
                    from _pytest.pathlib import import_path

                if PYTEST_GE_7_0:
                    module = import_path(fspath, root=self.config.rootpath)
                elif PYTEST_GT_5:
                    module = import_path(fspath)
                else:
                    module = fspath.pyimport()
            except ImportError:
                if self.config.getvalue("doctest_ignore_import_errors"):
                    pytest.skip("unable to import module %r" % fspath)
                else:
                    raise

        options = get_optionflags(self)

        # uses internal doctest module parsing mechanism
        finder = doctest.DocTestFinder()
        runner = doctest.DebugRunner(
            verbose=False, optionflags=options, checker=_get_checker())
        # End copied from pytest

        for method in module.__dict__.values():
            if _is_numpy_ufunc(method):
                for test in finder.find(method, module=module):
                    if test.examples:  # skip empty doctests
                        yield DoctestItem.from_parent(
                            self, name=test.name, runner=runner, dtest=test)
