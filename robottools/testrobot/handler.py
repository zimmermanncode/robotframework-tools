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

"""robottools.testrobot.handler

Making keyword calls from :class:`robottools.TestRobot` work with Python objects.

.. moduleauthor:: Stefan Zimmermann <zimmermann.code@gmail.com>
"""
__all__ = ['Handler']

from robot.utils import escape


class Handler(object):
    """Turns the Python arguments of a keyword call
       into the arguments for ``BuiltIn.run_keyword()``.

    - Strings are Robot data, so ``'${variable}'`` substitution still works
      (or literal text with ``resolve=False``).
    - Other objects are passed unstringified,
      as test variables set via the `set_variable` callable,
      because ``run_keyword()`` takes named arguments only as 'name=value' strings.
    """
    def __init__(self, set_variable, resolve=True):
        self.set_variable = set_variable
        self.resolve = resolve

    def resolve_arguments(self, args, kwargs):
        """Get the ``run_keyword()`` argument list
           for the Python `args` sequence and `kwargs` dict.
        """
        def arg(key, value):
            if isinstance(value, str):
                return value if self.resolve else escape(value)
            variable = '${__testrobot_%s}' % key
            self.set_variable(variable, value)
            return variable

        return ([arg(index, value) for index, value in enumerate(args)]
                + ['%s=%s' % (name, arg(name, value))
                   for name, value in kwargs.items()])
