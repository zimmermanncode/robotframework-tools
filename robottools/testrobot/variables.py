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

"""robottools.testrobot.variables

Robot Framework's Variables of a TestRobot's live session.

.. moduleauthor:: Stefan Zimmermann <zimmermann.code@gmail.com>
"""
__all__ = ['Variables']

import re

from robot.errors import DataError
from robot.libraries.BuiltIn import BuiltIn

_VARIABLE = re.compile(r'[$@&]\{([^{}\[\]=]+)\}')


class Variables(object):
    """The Variables of a TestRobot, looked up in its live session,
       with support for ``extra_getters`` (extra lookup sources),
       which are called with ``${...}`` style keys.
    """
    def __init__(self, context, extra_getters=None):
        self._context = context
        self._extra_getters = list(extra_getters or ())

    def __contains__(self, key):
        missing = object()
        return self._context.submit(
            lambda: BuiltIn().get_variable_value(key, missing)
        ) is not missing

    def __getitem__(self, key):
        """Also looks up ``self._extra_getters``.
        """
        if key in self:
            return self._context.submit(
                lambda: BuiltIn().get_variable_value(key))
        for getter in self._extra_getters:
            try:
                return getter(key)
            except (LookupError, DataError):
                pass
        raise DataError("Variable '%s' not found." % key)

    def __setitem__(self, key, value):
        self._context.submit(lambda: self._context.set_variable(key, value))

    def fill(self, strings):
        """Set the variables used in `strings` that are not defined yet
           from ``self._extra_getters``, so Robot can substitute them.
        """
        if not self._extra_getters:
            return
        for name in set(_VARIABLE.findall(' '.join(strings))):
            key = '${%s}' % name
            if key in self:
                continue
            for getter in self._extra_getters:
                try:
                    value = getter(key)
                except (LookupError, DataError):
                    continue
                self[key] = value
                break

    @property
    def current(self):
        # Like Robot's own Variables (as used by robotshell)
        return self

    def as_dict(self):
        """Get all variables as ``{'${name}': value}`` dict.
        """
        return self._context.submit(lambda: dict(BuiltIn().get_variables()))
