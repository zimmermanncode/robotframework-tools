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

"""robottools.testrobot.keyword

.. moduleauthor:: Stefan Zimmermann <zimmermann.code@gmail.com>
"""
__all__ = ['Keyword']

from robot.errors import HandlerExecutionFailed, RobotError


def debug_fail(failure):
    """Handles a Keyword FAIL in debugging mode
       by re-raising the exception that caused the FAIL.

    - `failure` is the exception that Robot Framework raised for the FAIL.
      Robot raises it while handling the keyword's own exception,
      which is therefore found in its ``__context__`` chain.
    - Does nothing for other kinds of failures.
    """
    if not isinstance(failure, HandlerExecutionFailed):
        return
    exc = failure
    while isinstance(exc, RobotError) and exc.__context__ is not None:
        exc = exc.__context__
    raise exc


class Keyword(object):
    """A Keyword of a :class:`robottools.TestRobot`'s Test Library,
       callable like a Python function.

    - Strings are Robot data (``'${variable}'`` substitution works),
      other arguments are passed as they are,
      and the Keyword's return value is returned.
    """
    def __init__(self, handler, context, debug=False):
        """Initialize with the Keyword's `handler` info
           (library name, keyword name, argument specs, documentation),
           as collected by :meth:`.context.Context.keywords`,
           and the :class:`.context.Context` of a TestRobot.
        """
        self._handler = handler
        self._context = context
        self._debug = debug
        self.libname, self.name, self.arguments, self.doc = handler

    @property
    def longname(self):
        return '%s.%s' % (self.libname, self.name)

    @property
    def __doc__(self):
        return '%r\n\n%s' % (self, self.doc)

    def __call__(self, *args, **kwargs):
        return self._context.call(
            self.longname, args, kwargs, debug=self._debug)

    def debug(self, *args, **kwargs):
        keyword = Keyword(self._handler, self._context, debug=True)
        return keyword(*args, **kwargs)

    def __repr__(self):
        return '[Keyword] %s [ %s ]' % (
            self.longname, ' | '.join(self.arguments))
