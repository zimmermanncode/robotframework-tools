"""TestRobot: keywords as Python calls in a live Robot Framework session.

Covers Python objects as arguments and return values, `${var}` resolution in string
arguments, imported libraries and variables kept between calls, debug mode, and two
TestRobots with separate libraries and variables in one process.
"""

from datetime import date

import pytest

from robottools import TestRobot as Robot  # (no `Test` prefix: pytest would collect it)

LIBRARY = '''
def get_year(value):
    return value.year


def boom():
    return 1 / 0
'''


@pytest.fixture
def robot(tmp_path, monkeypatch):
    (tmp_path / "Dates.py").write_text(LIBRARY, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    robot = Robot("Test")
    yield robot
    robot.shutdown()


def test_keywords_take_and_return_python_objects(robot):
    robot.Import("Collections")
    data = {"a": 1}
    robot.SetToDictionary(data, "b", 2)
    assert data == {"a": 1, "b": 2}
    assert robot.Collections.GetFromDictionary(data, "b") == 2

    robot["${data}"] = data
    assert robot.GetLength("${data}") == 2  # strings are Robot data
    assert robot["${data}"] is data


def test_libraries_and_debug_mode(robot):
    library = robot.Import("Dates")
    assert library.GetYear(date(2026, 11, 17)) == 2026
    with pytest.raises(Exception, match="division by zero") as failure:
        robot.Boom()
    assert type(failure.value).__name__ == "HandlerExecutionFailed"
    with pytest.raises(ZeroDivisionError):
        robot.Boom.debug()


def test_two_robots_are_separate(robot):
    other = Robot("Other")
    try:
        robot.Import("Collections")
        robot["${who}"] = "first"
        other["${who}"] = "second"
        assert (robot["${who}"], other["${who}"]) == ("first", "second")
        assert "Collections" in robot._libraries
        assert "Collections" not in other._libraries
    finally:
        other.shutdown()
