import pytest
from validate import (
    Validator, Typed, Integer, Float, String, Positive, 
    NonEmpty, PositiveInteger, PositiveFloat, NonEmptyString, 
    validated, enforce
)

def test_validator_basic():
    class MyVal(Validator):
        pass
    
    v = MyVal()
    assert v.check(10) == 10
    
    # Test __set_name__ and __set__
    class Container:
        x = MyVal()
    
    c = Container()
    c.x = 5
    assert c.x == 5
    assert c.__dict__['x'] == 5

def test_typed_validation():
    assert isinstance(Integer(), Typed)
    
    with pytest.raises(TypeError, match="expected <class 'int'>"):
        Integer.check("not an int")
    
    assert Integer.check(10) == 10
    assert Float.check(1.5) == 1.5
    assert String.check("hello") == "hello"

def test_composite_validators():
    # Positive
    assert Positive.check(0) == 0
    assert Positive.check(1) == 1
    with pytest.raises(ValueError, match="must be >= 0"):
        Positive.check(-1)
        
    # NonEmpty
    assert NonEmpty.check([1]) == [1]
    with pytest.raises(ValueError, match="must be non-empty"):
        NonEmpty.check([])
        
    # Combined (PositiveInteger)
    assert PositiveInteger.check(5) == 5
    with pytest.raises(ValueError, match="must be >= 0"):
        PositiveInteger.check(-5)
    with pytest.raises(TypeError, match="expected <class 'int'>"):
        PositiveInteger.check(1.5)
        
    # Combined (NonEmptyString)
    assert NonEmptyString.check("abc") == "abc"
    with pytest.raises(ValueError, match="must be non-empty"):
        NonEmptyString.check("")

def test_validated_decorator():
    @validated
    def func(a: Integer, b: PositiveInteger):
        return a + b
    
    assert func(1, 2) == 3
    with pytest.raises(TypeError, match="Bad Arguments"):
        func("a", -1)

def test_validated_return_check():
    @validated
    def func() -> PositiveInteger:
        return -1
    
    with pytest.raises(TypeError, match="Bad return: must be >= 0"):
        func()

    @validated
    def func_ok() -> PositiveInteger:
        return 1
    assert func_ok() == 1

def test_enforce_decorator():
    @enforce(a=Integer, return_=Positive)
    def func(a):
        return a
    
    assert func(5) == 5
    with pytest.raises(TypeError, match="Bad Arguments"):
        func(1.5)
    with pytest.raises(TypeError, match="Bad return: must be >= 0"):
        func(-1)

def test_validator_subclass_dict():
    # Verify __init_subclass__ populated the validators dict
    assert "Integer" in Validator.validators
    assert "Positive" in Validator.validators
    assert Validator.validators["Integer"] == Integer

def test_validated_no_annotations():
    @validated
    def simple():
        return True
    assert simple() is True

def test_enforce_no_retcheck():
    @enforce(a=Integer)
    def simple(a):
        return a
    assert simple(1) == 1

def test_validator_descriptor_name_assignment():
    v = Validator()
    v.__set_name__(None, "attr")
    assert v.name == "attr"

def test_validated_complex_args():
    # Test kwargs and mixed types
    @validated
    def func(a: Integer, b: String = "default"):
        return f"{a}{b}"
    
    assert func(1, b="test") == "1test"
    with pytest.raises(TypeError, match="Bad Arguments"):
        func(1.5, b=123)
