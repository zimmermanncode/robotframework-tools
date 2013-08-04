# robotframework-tools
#
# Tools for Robot Framework and Test Libraries.
#
# Copyright (C) 2013 Stefan Zimmermann <zimmermann.code@gmail.com>
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

"""robottools.keywords

- Provides a `moretools.simpledict` mapping type
  for storing Robot Test Library Keyword methods,
  provding dynamic Test-Case-like CamelCase access for interactive use.

- Defines the Test Library Keyword decorator base class
  which is used to identify methods as Robot Keywords
  and to apply certain additional options to these methods.

.. moduleauthor:: Stefan Zimmermann <zimmermann.code@gmail.com>
"""
__all__ = 'KeywordsDict', 'KeywordDecoratorType', 'InvalidKeywordOption',

import inspect
import re

from moretools import simpledict, camelize, decamelize

# A mapping type for storing Robot Library Keyword methods by name,
# providing additional `__getattr__` access with CamelCase Keyword names
KeywordsDict = simpledict(
  'Keywords',
  # convert lower_case keyword names to CamelCase attribute names
  key_to_attr=camelize,
  # convert CamelCase keyword attribute names back to lower_case
  attr_to_key=decamelize)

class InvalidKeywordOption(LookupError):
    pass

class KeywordDecoratorType(object):
    """The base type for a Test Library's `keyword` decorator.

    - Stores the Keyword method function
      in the Test Library's `keywords` mapping,
      after applying additional options (decorators) to the function.
    - Options are added with `__getattr__`,
      which generates new decorator class instances.
    """
    def __init__(self, keywords, *options):
        """Initialize with a Test Library's :class:`KeywordsDict` instance
           and additional `options` to apply to the decorated methods.
        """
        self.keywords = keywords

        for optionname in options:
            if not hasattr(type(self), 'option_' + optionname):
                raise InvalidKeywordOption(optionname)
        self.options = options

    @staticmethod
    def option_unicode_to_str(func):
        """Creates a wrapper method for Keyword method `func`
           which converts all unicode args to str.
        """
        def method(self, *args, **kwargs):
            iargs = (type(a) is unicode and str(a) or a for a in args)
            return func(self, *iargs, **kwargs)

        method.func_name = func.func_name
        return method

    @property
    def no_options(self):
        return type(self)(self.keywords)

    @property
    def reset_options(self):
        return type(self)(self.keywords)

    def __getattr__(self, name):
        """Returns a new Keyword decorator class instance
           with the given option added.
        """
        if not hasattr(type(self), 'option_' + name):
            raise AttributeError(name)
        return type(self)(self.keywords, name, *self.options)

    def __call__(self, func, name = None):
        """The actual Keyword method decorator function.

        - When manually called, an optional override `name` can be given.
        - All Keyword options added to this decorator class instance
          are applied.
        - The Keyword method function is stored
          in the Test Library's `keywords` mapping.
        """
        # Save original doc string
        doc = func.func_doc
        try:
            argspec = func.argspec
        except AttributeError:
            argspec = inspect.getargspec(func)
        # Apply options
        for optionname in self.options:
            decorator = getattr(type(self), 'option_' + optionname)
            func = decorator(func)
        if not name:
            name = func.func_name
        if func.func_doc:
            # Update saved doc string
            doc = func.func_doc

        # Use at least one wrapper to make the assignments below always work
        def keyword_method(self, *args, **kwargs):
            return func(self, *args, **kwargs)

        # Keep existing (or explicitly given) method name
        keyword_method.func_name = name
        # Keep method doc string
        keyword_method.func_doc = doc
        # Store original method argspec
        keyword_method.argspec = argspec
        # Add method to the Library's Keywords mapping
        self.keywords[name] = keyword_method
        return keyword_method
