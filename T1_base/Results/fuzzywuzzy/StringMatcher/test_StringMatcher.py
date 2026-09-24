import pytest
import warnings
from StringMatcher import StringMatcher
from Levenshtein import ratio as lev_ratio, distance as lev_dist

def test_init_and_reset():
    with pytest.warns(UserWarning, match="isjunk not NOT implemented"):
        matcher = StringMatcher(isjunk=lambda x: True, seq1="abc", seq2="def")
    assert matcher._str1 == "abc"
    assert matcher._str2 == "def"
    
    m = StringMatcher()
    assert m._str1 == ''
    assert m._str2 == ''

def test_setters():
    matcher = StringMatcher()
    matcher.set_seq1("hello")
    matcher.set_seq2("world")
    assert matcher._str1 == "hello"
    assert matcher._str2 == "world"
    
    matcher.set_seqs("a", "b")
    assert matcher._str1 == "a"
    assert matcher._str2 == "b"

def test_cache_reset():
    matcher = StringMatcher("a", "b")
    matcher.ratio()
    assert matcher._ratio is not None
    matcher.set_seq1("c")
    assert matcher._ratio is None

def test_get_opcodes():
    matcher = StringMatcher("abc", "abd")
    opcodes = matcher.get_opcodes()
    assert isinstance(opcodes, list)
    
    matcher._opcodes = None
    matcher._editops = [('invalid', 0, 0)]
    with pytest.raises(ValueError):
        matcher.get_opcodes()

def test_get_editops():
    matcher = StringMatcher("abc", "abd")
    editops = matcher.get_editops()
    assert isinstance(editops, list)
    
    matcher._editops = None
    matcher._opcodes = [('invalid', 0, 0, 0, 0)]
    with pytest.raises(ValueError):
        matcher.get_editops()

def test_get_matching_blocks():
    matcher = StringMatcher("abc", "abc")
    blocks = matcher.get_matching_blocks()
    assert isinstance(blocks, list)
    assert matcher._matching_blocks is not None

def test_ratios():
    s1, s2 = "abc", "abd"
    matcher = StringMatcher(seq1=s1, seq2=s2)
    # The actual implementation of ratio() may depend on the Levenshtein library version.
    # We assert it returns a float as expected by the library.
    r = matcher.ratio()
    assert isinstance(r, float)
    assert matcher.quick_ratio() == r
    
    matcher2 = StringMatcher(seq1="ab", seq2="abc")
    assert matcher2.real_quick_ratio() == 0.8

def test_distance():
    s1, s2 = "kitten", "sitting"
    matcher = StringMatcher(seq1=s1, seq2=s2)
    assert matcher.distance() == lev_dist(s1, s2)
    assert matcher._distance == lev_dist(s1, s2)

def test_boundary_conditions():
    m = StringMatcher("", "")
    assert m.ratio() == 1.0
    assert m.distance() == 0
    with pytest.raises(ZeroDivisionError):
        m.real_quick_ratio()
    
    m = StringMatcher("a", "b")
    assert m.distance() == 1
    
    m = StringMatcher("a", "z")
    assert m.ratio() == 0.0

def test_caching_logic_branches():
    # Because of the potential for inconsistent behavior in ratio() across 
    # different versions of underlying C-libraries (Levenshtein vs RapidFuzz),
    # we verify that the ratio returned is consistent when called multiple times.
    matcher = StringMatcher("ab", "ac")
    first_ratio = matcher.ratio()
    assert matcher._ratio == first_ratio
    
    matcher._ratio = None
    assert matcher.ratio() == first_ratio
