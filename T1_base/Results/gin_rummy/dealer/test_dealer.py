import pytest
import numpy as np
from dealer import GinRummyDealer
from gin_rummy import Player

class MockPlayer:
    def __init__(self):
        self.hand = []
        self.called_did_populate = False
    
    def did_populate_hand(self):
        self.called_did_populate = True

def test_dealer_initialization():
    # Verify deck is shuffled based on fixed seed
    seed = 42
    np_random = np.random.RandomState(seed)
    dealer = GinRummyDealer(np_random)
    
    assert len(dealer.shuffled_deck) == 52
    assert len(dealer.stock_pile) == 52
    assert dealer.discard_pile == []
    
    # Check that it's a copy, not a reference
    assert dealer.shuffled_deck is not dealer.stock_pile
    assert dealer.shuffled_deck == dealer.stock_pile

def test_deal_cards_boundary():
    seed = 123
    np_random = np.random.RandomState(seed)
    dealer = GinRummyDealer(np_random)
    player = MockPlayer()
    
    # Test dealing 0 cards
    dealer.deal_cards(player, 0)
    assert len(player.hand) == 0
    assert player.called_did_populate is True
    
    # Reset mock
    player.called_did_populate = False
    
    # Test dealing 1 card
    dealer.deal_cards(player, 1)
    assert len(player.hand) == 1
    assert len(dealer.stock_pile) == 51
    assert player.called_did_populate is True

def test_deal_cards_multiple():
    seed = 777
    np_random = np.random.RandomState(seed)
    dealer = GinRummyDealer(np_random)
    player = MockPlayer()
    
    # Test dealing multiple cards
    num_to_deal = 10
    dealer.deal_cards(player, num_to_deal)
    
    assert len(player.hand) == num_to_deal
    assert len(dealer.stock_pile) == 52 - num_to_deal
    assert player.called_did_populate is True

def test_stockpile_exhaustion():
    # This checks behavior when popping from empty list (raises IndexError)
    seed = 1
    np_random = np.random.RandomState(seed)
    dealer = GinRummyDealer(np_random)
    player = MockPlayer()
    
    # Exhaust the stock pile
    dealer.deal_cards(player, 52)
    assert len(dealer.stock_pile) == 0
    
    # Next deal should raise IndexError
    with pytest.raises(IndexError):
        dealer.deal_cards(player, 1)

def test_dealer_shuffling_consistency():
    # Verify that different seeds produce different orders
    seed_a = 1
    seed_b = 2
    
    dealer_a = GinRummyDealer(np.random.RandomState(seed_a))
    dealer_b = GinRummyDealer(np.random.RandomState(seed_b))
    
    assert dealer_a.shuffled_deck != dealer_b.shuffled_deck
