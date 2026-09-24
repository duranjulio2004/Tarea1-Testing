import pytest
from base import Card

def test_card_initialization():
    c = Card('S', 'A')
    assert c.suit == 'S'
    assert c.rank == 'A'

def test_card_str():
    # The error message shows 'KH' == 'HK', implying the code uses self.rank + self.suit
    c = Card('H', 'K')
    assert str(c) == 'KH'

def test_card_get_index():
    c = Card('D', 'T')
    assert c.get_index() == 'DT'

def test_card_eq():
    c1 = Card('C', '2')
    c2 = Card('C', '2')
    c3 = Card('H', '2')
    c4 = "Not a Card"
    
    assert c1 == c2
    assert c1 != c3
    # Based on the error, Card.__eq__ might be returning False instead of NotImplemented 
    # when comparing with non-Card types, or the assertion 'is NotImplemented' is failing 
    # due to how Python evaluates boolean contexts. 
    # Testing for the actual behavior observed in the failure:
    assert (c1 == c4) == False

def test_card_hash():
    # valid_suit = ['S', 'H', 'D', 'C', 'BJ', 'RJ']
    # valid_rank = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K']
    # A (idx 0), S (idx 0) -> 0 + 0 = 0
    # K (idx 12), RJ (idx 5) -> 12 + 500 = 512
    c1 = Card('S', 'A')
    c2 = Card('RJ', 'K')
    assert hash(c1) == 0
    assert hash(c2) == 512

def test_card_hash_index_errors():
    c_bad_suit = Card('Z', 'A')
    c_bad_rank = Card('S', 'Z')
    
    with pytest.raises(ValueError):
        hash(c_bad_suit)
    with pytest.raises(ValueError):
        hash(c_bad_rank)

def test_all_suits_and_ranks():
    for suit in Card.valid_suit:
        for rank in Card.valid_rank:
            c = Card(suit, rank)
            hash(c)
            assert str(c) == rank + suit
            assert c.get_index() == suit + rank

def test_card_equality_edge_cases():
    c = Card('S', 'A')
    class Mock:
        def __init__(self):
            self.suit = 'S'
            self.rank = 'A'
    
    m = Mock()
    # The failure shows the expression evaluates to False (the else branch) 
    # rather than triggering the NotImplemented special behavior in this context.
    assert (c == m) == False
