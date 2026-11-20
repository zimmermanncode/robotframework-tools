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

"""robottools.testrobot.output

.. moduleauthor:: Stefan Zimmermann <zimmermann.code@gmail.com>
"""
__all__ = ['Output']

import sys
import threading

from robot.output import LOGGER, LEVELS as LOG_LEVELS
from robot.output.loggerapi import LoggerApi


class Output(LoggerApi):
    """Prints the log messages of a TestRobot's Keywords.

    - Registered with Robot Framework's global ``LOGGER``,
      so it gets the messages of all TestRobots in the process
      and prints only those logged in its own TestRobot's thread.
    - Prints to the stream that was ``sys.stdout`` on creation:
      ``sys.stdout`` itself is captured by Robot while a Keyword runs.
    """
    def __init__(self, log_level='INFO', stream=None):
        self.log_level = log_level
        self.stream = stream or sys.stdout
        self.thread = None  # set by the TestRobot's Context
        self.quiet = False  # set while the TestRobot itself sets variables
        LOGGER.register_logger(self)

    def set_log_level(self, level):
        old = self.log_level
        self.log_level = str(level).upper()
        return old

    def log_message(self, message):
        if self.quiet or threading.current_thread() is not self.thread:
            return
        # (FAIL is not printed: the failure is raised to the caller anyway)
        if message.level in ('FAIL', 'SKIP', 'NONE'):
            return
        level = LOG_LEVELS.get(message.level)
        if level is not None and level >= LOG_LEVELS.get(self.log_level, 0):
            print('[%s] %s' % (message.level, message.message),
                  file=self.stream)

    def close(self):
        LOGGER.unregister_logger(self)
