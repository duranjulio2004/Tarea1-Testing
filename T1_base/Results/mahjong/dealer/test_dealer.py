import pytest
import numpy as np
from dealer import MahjongDealer

# Mock class to simulate the player object used by dealer.deal_cards
class MockPlayer:
    def __init__(self):
        self.hand = []

def test_dealer_initialization():
    """Test proper initialization and shuffling."""
    seed = 42
    rng = np.random.RandomState(seed)
    dealer = MahjongDealer(rng)
    
    assert len(dealer.deck) == 136
    assert dealer.table == []
    
    # Verify randomness is deterministic based on seed
    rng_copy = np.random.RandomState(seed)
    dealer_check = MahjongDealer(rng_copy)
    assert dealer.deck[0].get_str() == dealer_check.deck[0].get_str()

def test_deal_cards_logic():
    """Test dealing cards correctly reduces deck and adds to player hand."""
    rng = np.random.RandomState(1)
    dealer = MahjongDealer(rng)
    player = MockPlayer()
    
    # The dealer constructor calls self.shuffle().
    # We track exactly what is at the end of the shuffled deck before calling deal_cards.
    target_card = dealer.deck[-1]
    
    deal_count = 1
    dealer.deal_cards(player, deal_count)
    
    assert len(player.hand) == deal_count
    # The last card of the deck (pre-deal) should now be the first (and only) card in hand
    assert player.hand[0].get_str() == target_card.get_str()

def test_deal_cards_boundary_zero():
    """Test dealing zero cards."""
    rng = np.random.RandomState(1)
    dealer = MahjongDealer(rng)
    player = MockPlayer()
    
    initial_len = len(dealer.deck)
    dealer.deal_cards(player, 0)
    assert len(player.hand) == 0
    assert len(dealer.deck) == initial_len

def test_deal_cards_excessive():
    """Test behavior when popping more cards than available."""
    rng = np.random.RandomState(1)
    dealer = MahjongDealer(rng)
    player = MockPlayer()
    
    # The loop 'for _ in range(num)' will pop cards until the deck is empty,
    # then raise IndexError on the next pop.
    with pytest.raises(IndexError):
        dealer.deal_cards(player, 137)

def test_shuffle_randomness():
    """Verify that shuffle actually changes the deck order."""
    rng = np.random.RandomState(1)
    dealer = MahjongDealer(rng)
    
    from utils import init_deck
    unshuffled = init_deck()
    
    dealer_str = [c.get_str() for c in dealer.deck]
    unshuffled_str = [c.get_str() for c in unshuffled]
    
    # Verify shuffle occurred
    assert dealer_str != unshuffled_str

def test_dealer_table_mutation():
    """Verify table property interaction."""
    rng = np.random.RandomState(1)
    dealer = MahjongDealer(rng)
    
    card = dealer.deck.pop()
    dealer.table.append(card)
    
    assert len(dealer.table) == 1
    assert dealer.table[0] == card
