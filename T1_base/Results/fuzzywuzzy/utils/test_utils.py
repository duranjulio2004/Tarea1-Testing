import pytest
from utils import (
    validate_string, check_for_equivalence, check_for_none, check_empty_string,
    asciidammit, make_type_consistent, full_process, intr
)

def test_validate_string():
    assert validate_string("abc") is True
    assert validate_string("") is False
    assert validate_string(None) is False
    assert validate_string(123) is False

def test_decorators():
    @check_for_equivalence
    @check_for_none
    @check_empty_string
    def mock_func(a, b):
        return "ok"

    # Test equivalence path (100)
    assert mock_func("a", "a") == 100
    # Test none path (0)
    assert mock_func(None, "b") == 0
    # Test empty string path (0)
    assert mock_func("a", "") == 0
    # Test normal path
    assert mock_func("a", "b") == "ok"

def test_asciidammit():
    # Test string input (ascii)
    assert asciidammit("hello") == "hello"
    # Test non-ascii (remove high range)
    assert asciidammit("café") == "caf"
    # Test numeric input (coerced to unicode/string)
    assert asciidammit(123) == "123"

def test_make_type_consistent():
    # Test both str
    assert make_type_consistent("a", "b") == ("a", "b")
    # Test non-string input (forces to unicode/str)
    res1, res2 = make_type_consistent(1, 2)
    assert res1 == "1"
    assert res2 == "2"

def test_full_process():
    # Based on the failure: StringProcessor.replace_non_letters_non_numbers_with_whitespace 
    # replaces '!' with a space, resulting in double spaces that are not fully stripped
    # by StringProcessor.strip() which is just string.strip() (outer edges only).
    assert full_process("  Hello! 123  ") == "hello  123"
    assert full_process("café 123", force_ascii=True) == "caf 123"
    assert full_process("!!!") == ""

def test_intr():
    assert intr(1.2) == 1
    assert intr(1.7) == 2
    # Rounding .5 behavior in Python 3
    assert intr(0.5) == 0
    assert intr(1.5) == 2

def test_asciidammit_types():
    # Branch coverage: Ensure type check branches are hit
    # type(s) is str vs type(s) is unicode (same in py3) vs else
    assert asciidammit("text") == "text"
    assert asciidammit(123) == "123"

def test_make_type_consistent_branches():
    # Branch coverage for isinstance(s1, str) and isinstance(s2, str)
    assert make_type_consistent("a", "b") == ("a", "b")
    # Branch coverage for else
    assert make_type_consistent(1, "b") == ("1", "b")

def test_validate_string_edge():
    # Verifying TypeError is caught and returns False
    class NoLen:
        pass
    assert validate_string(NoLen()) is False
    assert validate_string(None) is False
