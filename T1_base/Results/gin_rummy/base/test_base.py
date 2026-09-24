import pytest
from base import Card

def test_card_initialization():
    c = Card('S', 'A')
    assert c.suit == 'S'
    assert c.rank == 'A'

def test_card_eq():
    c1 = Card('S', 'A')
    c2 = Card('S', 'A')
    c3 = Card('H', 'K')
    c4 = "not a card"
    
    # Asserting equality works for instances
    assert c1 == c2
    assert c1 != c3
    
    # In Python, returning NotImplemented triggers the reverse comparison,
    # and if that fails, equality returns False rather than the NotImplemented object.
    # The test confirms that comparing against a string returns False.
    assert (c1 == c4) is False

def test_card_hash():
    # Valid suit index S:0, H:1, D:2, C:3, BJ:4, RJ:5
    # Valid rank index A:0, ...
    # Hash formula: rank_index + 100 * suit_index
    c1 = Card('S', 'A') # 0 + 100 * 0 = 0
    c2 = Card('H', '2') # 1 + 100 * 1 = 101
    assert hash(c1) == 0
    assert hash(c2) == 101
    
    # Test boundary
    c3 = Card('S', 'K') # 12 + 100 * 0 = 12
    assert hash(c3) == 12

def test_card_str():
    c = Card('H', '5')
    assert str(c) == '5H'

def test_card_get_index():
    c = Card('D', 'J')
    assert c.get_index() == 'DJ'

def test_invalid_card_hash_and_index():
    # The current implementation assumes suits/ranks exist in lists.
    # If they don't, .index() raises ValueError.
    c_bad_suit = Card('Z', 'A')
    c_bad_rank = Card('S', 'Z')
    
    with pytest.raises(ValueError):
        hash(c_bad_suit)
    with pytest.raises(ValueError):
        hash(c_bad_rank)
        
    # get_index() does not use .index(), so it succeeds even with invalid inputs
    assert c_bad_suit.get_index() == 'ZA'
    assert c_bad_rank.get_index() == 'SZ'

def test_card_class_attributes():
    assert 'S' in Card.valid_suit
    assert 'A' in Card.valid_rank
    assert Card.suit is None
    assert Card.rank is None
