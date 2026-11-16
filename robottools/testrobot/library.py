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

"""robottools.testrobot.library

.. moduleauthor:: Stefan Zimmermann <zimmermann.code@gmail.com>
"""
__all__ = ['TestLibrary']

from robot.utils import normalize

from .keyword import Keyword


class TestLibrary(object):
    """A Test Library imported by a :class:`robottools.TestRobot`,
       with its Keywords as (CamelCase) attributes.
    """
    def __init__(self, lib, args=None, context=None):
        """Initialize with the library name `lib`
           and the :class:`.context.Context` of the TestRobot that imported it.

        - `args` are not used any more: the library is not imported again.
        - Without `context`, only `.name` is available.
        """
        self._library = lib
        self.name = lib
        self._context = context

    @property
    def keywords(self):
        if self._context is None:
            return []
        return [Keyword(handler, self._context)
                for handler in self._context.keywords()[self.name]]

    def __iter__(self):
        return iter(self.keywords)

    def __getitem__(self, name):
        normalized = normalize(name, ignore='_')
        for keyword in self.keywords:
            if normalize(keyword.name, ignore='_') == normalized:
                return keyword
        raise KeyError(name)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

    def __dir__(self):
        return [keyword.name.title().replace(' ', '')
                for keyword in self.keywords]

    @property
    def __doc__(self):
        return '%r\n\n%s' % (self, '\n'.join(
            '* %r' % keyword for keyword in self.keywords))

    def __repr__(self):
        return '[Library] %s' % self.name
