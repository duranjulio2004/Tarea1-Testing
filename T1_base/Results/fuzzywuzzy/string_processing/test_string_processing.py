import pytest
from string_processing import StringProcessor

def test_replace_non_letters_non_numbers_with_whitespace():
    """
    Tests for replace_non_letters_non_numbers_with_whitespace.
    """
    assert StringProcessor.replace_non_letters_non_numbers_with_whitespace("") == ""
    assert StringProcessor.replace_non_letters_non_numbers_with_whitespace("abc123") == "abc123"
    assert StringProcessor.replace_non_letters_non_numbers_with_whitespace("a!b@c#1$2%3") == "a b c 1 2 3"
    assert StringProcessor.replace_non_letters_non_numbers_with_whitespace("a  b!!c") == "a  b  c"
    assert StringProcessor.replace_non_letters_non_numbers_with_whitespace("café!") == "café "

def test_strip():
    """
    Tests StringProcessor.strip method.
    """
    assert StringProcessor.strip("  abc  ") == "abc"
    assert StringProcessor.strip("abc") == "abc"
    assert StringProcessor.strip("") == ""
    assert StringProcessor.strip("\t\n abc \r") == "abc"

def test_to_lower_case():
    """
    Tests StringProcessor.to_lower_case.
    """
    assert StringProcessor.to_lower_case("ABC") == "abc"
    assert StringProcessor.to_lower_case("abc") == "abc"
    assert StringProcessor.to_lower_case("123!A") == "123!a"
    assert StringProcessor.to_lower_case("") == ""

def test_to_upper_case():
    """
    Tests StringProcessor.to_upper_case.
    """
    assert StringProcessor.to_upper_case("abc") == "ABC"
    assert StringProcessor.to_upper_case("ABC") == "ABC"
    assert StringProcessor.to_upper_case("123!a") == "123!A"
    assert StringProcessor.to_upper_case("") == ""

def test_invalid_input_types():
    """
    Tests behavior with non-string inputs.
    The code uses native string methods, so passing integers raises TypeError.
    """
    # Regex sub raises TypeError on non-string
    with pytest.raises(TypeError):
        StringProcessor.replace_non_letters_non_numbers_with_whitespace(123)
        
    # strip, lower, upper are unbound string methods (descriptors),
    # calling them with non-str raises TypeError on the descriptor check.
    with pytest.raises(TypeError):
        StringProcessor.strip(123)
    
    with pytest.raises(TypeError):
        StringProcessor.to_lower_case(123)
        
    with pytest.raises(TypeError):
        StringProcessor.to_upper_case(123)

def test_regex_class_property():
    """
    Verify the regex is compiled and available as a class attribute.
    """
    assert hasattr(StringProcessor, 'regex')
    assert StringProcessor.regex.pattern == r"(?ui)\W"
