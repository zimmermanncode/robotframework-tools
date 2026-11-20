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

"""robottools.testrobot.context

.. moduleauthor:: Stefan Zimmermann <zimmermann.code@gmail.com>
"""
__all__ = ['Context', 'serve']  # `serve` is this module's Keyword (see below)

import queue
import sys
import threading

from robot.api import TestSuite
from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn
from robot.output import librarylogger
from robot.running import EXECUTION_CONTEXTS

from .handler import Handler
from .keyword import debug_fail

# This module is imported as Test Library by every Context's suite,
# for its `TestRobot Serve` Keyword only:
ROBOT_AUTO_KEYWORDS = False

_CONTEXTS = {}


@keyword('TestRobot Serve')
def serve(context_id):
    """Blocks the only test of a Context's suite
       and runs the calls from the Context's queue in the live execution context.
    """
    context = _CONTEXTS[context_id]
    # Robot captures sys.stdout/stderr (process-wide) while a Keyword runs,
    # and this one runs as long as the Context: give the streams back meanwhile.
    captured = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = context.streams
    context._outbox.put((True, None))  # ready
    try:
        _serve(context._inbox, context._outbox)
    finally:
        sys.stdout, sys.stderr = captured


def _serve(inbox, outbox):
    own = EXECUTION_CONTEXTS.current
    while True:
        call = inbox.get()
        if call is None:
            break
        # Several TestRobots in one process: Robot keeps one global stack of
        # execution contexts, with the one started last on top.
        # So put this one on top for each call (the only private Robot API used):
        stack = EXECUTION_CONTEXTS._contexts
        pushed = stack[-1] is not own
        if pushed:
            stack.append(own)
        try:
            outbox.put((True, call()))
        except BaseException as exc:  # handed to the caller
            outbox.put((False, exc))
        finally:
            if pushed:
                stack.pop()
    # The suite's end pops the top execution context: make sure it is this one.
    stack = EXECUTION_CONTEXTS._contexts
    if stack[-1] is not own:
        stack.remove(own)
        stack.append(own)


class Context(object):
    """The live Robot Framework execution of a :class:`robottools.TestRobot`.

    - Runs a suite in a separate thread, whose only test blocks in the
      `TestRobot Serve` Keyword and runs the TestRobot's calls
      in the live execution context, so imported Test Libraries,
      Variables and library states persist between calls.
    """
    def __init__(self, testrobot):
        self.testrobot = testrobot
        self.output = testrobot._output
        self.streams = sys.stdout, sys.stderr
        self._inbox, self._outbox = queue.Queue(), queue.Queue()
        context_id = str(id(self))
        _CONTEXTS[context_id] = self

        suite = TestSuite(name=testrobot.name)
        suite.resource.imports.library(__name__)
        suite.tests.create(name=testrobot.name).body.create_keyword(
            'TestRobot Serve', args=[context_id])
        self._thread = threading.Thread(
            target=self._run, args=(suite,), daemon=True)
        self.output.thread = self._thread
        self._thread.start()
        self._result()

    def _run(self, suite):
        # Robot ignores Library log messages from threads it doesn't know.
        # (robot.run() registers its own thread the same way.)
        name = threading.current_thread().name
        threads = librarylogger.LOGGING_THREADS
        if name not in threads:
            if isinstance(threads, list):  # Robot 7.x
                threads.append(name)
            else:  # tuple in Robot 7.0
                librarylogger.LOGGING_THREADS = threads + (name,)
        suite.run(output=None, log=None, report=None, console='none')

    def _result(self, debug=False):
        while True:  # don't hang if the suite thread died
            try:
                ok, value = self._outbox.get(timeout=0.5)
                break
            except queue.Empty:
                if not self._thread.is_alive():
                    raise RuntimeError(
                        "TestRobot '%s' has ended." % self.testrobot.name
                    ) from None
        if ok:
            return value
        if debug:
            debug_fail(value)
        raise value

    def submit(self, func, debug=False):
        """Run `func()` in the live execution context and return its result.
        """
        self._inbox.put(func)
        return self._result(debug)

    def set_variable(self, name, value):
        """Set a test variable (from inside the live execution context).
        """
        self.output.quiet = True  # don't print Robot's log message about it
        try:
            BuiltIn().set_test_variable(name, value)
        finally:
            self.output.quiet = False

    def call(self, name, args=(), kwargs=None, resolve=True, debug=False):
        """Run Keyword `name` with Python `args` and `kwargs`.

        - See :class:`.handler.Handler` for how arguments are passed.
        - Undefined variables used in string arguments
          are looked up in the TestRobot's variables' extra getters.
        """
        kwargs = kwargs or {}
        if resolve:
            self.testrobot._variables.fill(
                [value for value in (*args, *kwargs.values())
                 if isinstance(value, str)])
        handler = Handler(self.set_variable, resolve=resolve)
        return self.submit(lambda: BuiltIn().run_keyword(
            name, *handler.resolve_arguments(args, kwargs)), debug)

    def keywords(self):
        """Get ``{library name: [(library name, keyword name, args, doc), ...]}``
           of all imported Test Libraries.
        """
        def collect():
            return {lib.name: [(lib.name, kw.name, [str(arg) for arg in kw.args],
                                kw.doc) for kw in lib.keywords]
                    for lib in EXECUTION_CONTEXTS.current.namespace.libraries
                    if lib.name != __name__}

        return self.submit(collect)

    def close(self):
        self._inbox.put(None)
        self._thread.join()
