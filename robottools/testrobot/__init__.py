# robotframework-tools
#
# Python Tools for Robot Framework and Test Libraries.
#
# Copyright (C) 2013-2016 Stefan Zimmermann <zimmermann.code@gmail.com>
#
# robotframework-tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# robotframework-tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with robotframework-tools. If not, see <http://www.gnu.org/licenses/>.

"""robottools.testrobot

Provides the interactive TestRobot interface.

.. moduleauthor:: Stefan Zimmermann <zimmermann.code@gmail.com>
"""
__all__ = [
    'TestRobot',
    'TestResult', # from .result
]

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from robot.api import ExecutionResult
from robot.errors import DataError
from robot.utils import normalize

from .variables import Variables
from .output import Output
from .context import Context
from .library import TestLibrary
from .keyword import Keyword
from .result import TestResult


class TestRobot:  # (zetup.object):
    """An interactive Robot Framework interface.

    - Runs a live Robot Framework session (see :class:`.context.Context`),
      which keeps imported Test Libraries and Variables between calls.
    """
    def __init__(self, name, BuiltIn=True, variable_getters=None):
        """Initialize with a `name`
           and optional additional variable lookup functions.

        - If a Variable is not found in the Robot's Variables dictionary,
          the `variable_getters` will be called in the given order
          with the Variable string in Robot syntax ($/@{...})
          until no `LookupError` or `DataError` is raised.
          (Used by the `robot_shell` to extend Variables lookup
           to IPython's `user_ns` and Python's `builtins`).

        :param BuiltIn: Not used any more:
          Robot Framework always imports its BuiltIn Library.
        :param variable_getters: A sequence of callables.
        """
        self.name = name
        self.debug = False
        self._output = Output()
        self._context = Context(testrobot=self)
        self._variables = Variables(
            self._context, extra_getters=variable_getters)

    @property
    def _libraries(self):
        """Get the TestRobot's imported Test Libraries
           as ``{name: TestLibrary}`` dict.
        """
        return {name: TestLibrary(name, context=self._context)
                for name in self._context.keywords()}

    @property
    def __doc__(self):
        """Dynamic doc string, listing imported Test Libraries.
        """
        return '%s\n\n%s' % (repr(self), '\n\n'.join(sorted(
            '* [Import] ' + name for name in self._libraries)))

    def Import(self, lib, args=None, alias=None):
        """Import a Test Library with an optional `alias` name.
        """
        before = set(self._libraries)
        # (`resolve`: the `AS` marker must not be escaped)
        self._context.call('Import Library', (
            str(lib), *(args or ()), *(['AS', alias] if alias else [])))
        imported = set(self._libraries) - before
        if imported:
            name = imported.pop()
        else:  # was already imported
            name = alias or Path(str(lib)).stem.rsplit('.', 1)[-1]
        return TestLibrary(name, context=self._context)

    def Run(self, path, **options):
        """Run the test suite(s) at `path` in a separate Robot Framework process
           with `robot.run()` `options`.

        - Returns a :class:`.result.TestResult`.
        - `debug` is not supported any more:
          exceptions can't be re-raised from another process.
        """
        options.pop('debug', None)
        with tempfile.TemporaryDirectory() as outdir:
            run_options = dict(options, outputdir=outdir, output='output.xml')
            code = ('import json, sys, robot; sys.exit(robot.run('
                    '*sys.argv[1:], **json.loads(sys.stdin.read())))')
            subprocess.run([sys.executable, '-c', code, str(path)],
                           input=json.dumps(run_options, default=str),
                           text=True)
            result = ExecutionResult(str(Path(outdir) / 'output.xml'))
        return TestResult(result, **options)

    def __getitem__(self, name):
        """Get variables (with $/@{...} syntax),
           Test Libraries and Keywords by name.

        - Keyword names can be in any case (like in a Test Script).
        """
        if any(name.startswith(c) for c in '$@&'):
            try:
                return self._variables[name]
            except DataError as e:
                raise KeyError(str(e))
        keywords = self._context.keywords()
        if name in keywords:
            return TestLibrary(name, context=self._context)
        libname, _, kwname = name.rpartition('.')
        normalized = normalize(kwname, ignore='_')
        for lib, handlers in keywords.items():
            if libname and normalize(lib) != normalize(libname):
                continue
            for handler in handlers:
                if normalize(handler[1], ignore='_') == normalized:
                    keyword = Keyword(handler, context=self._context)
                    if self.debug:
                        return keyword.debug
                    return keyword
        raise KeyError("No Test Library or Keyword named '%s'." % name)

    def __setitem__(self, name, value):
        """Set variables (with ${...} syntax).
        """
        self._variables[name] = value

    def __getattr__(self, name):
        """Get Robot Variables, Test Libraries and Keywords by name.

        - Keyword names can be in any case (lower_case, CamelCase, ...),
          but CamelCase is the preferred style.
        """
        if name.startswith('_'):
            raise AttributeError(name)
        try: # Delegate to self.__getitem__:
            return self[name]
        except KeyError:
            try:
                return self._variables['${%s}' % name]
            except DataError:
                raise AttributeError(
                    "No Test Library, Keyword or Variable named '%s'."
                    % name)

    def __dir__(self):
        """List all Robot Variables (UPPER_CASE),
           Test Libraries and Keyword (CamelCase) names,
           which are valid Python identifiers.
        """
        names = list(super(TestRobot, self).__dir__())
        for name in self._variables.as_dict():
            name = name[2:-1] # Strip ${}
            if name.isidentifier():
                names.append(name.upper())
        for alias, lib in self._libraries.items():
            names.append(alias)
            # dir() returns the Library's CamelCase Keyword names:
            names.extend(dir(lib))
        return names

    def shutdown(self):
        """End the TestRobot's Robot Framework session.
        """
        self._context.close()
        self._output.close()

    def __str__(self):
        return self.name

    def __repr__(self):
        return '[Robot] %s' % self
