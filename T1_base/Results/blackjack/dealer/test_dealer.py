import pytest
import numpy as np
from dealer import BlackjackDealer, init_standard_deck
from blackjack import Card

class MockPlayer:
    def __init__(self):
        self.hand = []

@pytest.fixture
def rng():
    return np.random.RandomState(42)

def test_init_standard_deck():
    deck = init_standard_deck()
    assert len(deck) == 52
    assert isinstance(deck[0], Card)
    # Check for uniqueness (simple heuristic)
    assert len(set(str(c) for c in deck)) == 52

def test_dealer_initialization_single_deck(rng):
    dealer = BlackjackDealer(rng, num_decks=1)
    assert len(dealer.deck) == 52
    assert dealer.num_decks == 1
    assert dealer.status == 'alive'
    assert dealer.score == 0

def test_dealer_initialization_multi_deck(rng):
    num_decks = 2
    dealer = BlackjackDealer(rng, num_decks=num_decks)
    assert len(dealer.deck) == 52 * num_decks

def test_dealer_initialization_infinite_deck(rng):
    # num_decks=0 triggers infinite/no-pop behavior
    dealer = BlackjackDealer(rng, num_decks=0)
    assert len(dealer.deck) == 52

def test_shuffle(rng):
    dealer = BlackjackDealer(rng, num_decks=1)
    original_deck = list(dealer.deck)
    dealer.shuffle()
    assert dealer.deck != original_deck
    assert len(dealer.deck) == 52

def test_deal_card_standard_deck(rng):
    dealer = BlackjackDealer(rng, num_decks=1)
    player = MockPlayer()
    
    initial_deck_size = len(dealer.deck)
    dealer.deal_card(player)
    
    assert len(player.hand) == 1
    assert len(dealer.deck) == initial_deck_size - 1

def test_deal_card_infinite_deck(rng):
    # Testing num_decks = 0 branch
    dealer = BlackjackDealer(rng, num_decks=0)
    player = MockPlayer()
    
    initial_deck_size = len(dealer.deck)
    dealer.deal_card(player)
    
    assert len(player.hand) == 1
    assert len(dealer.deck) == initial_deck_size  # Should not pop

@pytest.mark.parametrize("num_decks", [1, 2, 0])
def test_deal_card_boundary_conditions(rng, num_decks):
    # Verify dealing multiple times works
    dealer = BlackjackDealer(rng, num_decks=num_decks)
    player = MockPlayer()
    
    for _ in range(5):
        dealer.deal_card(player)
        
    assert len(player.hand) == 5
    if num_decks != 0:
        assert len(dealer.deck) == (52 * num_decks) - 5
    else:
        assert len(dealer.deck) == 52

def test_init_standard_deck_values():
    deck = init_standard_deck()
    # Verify specific cards exist
    assert any(c.rank == 'A' and c.suit == 'S' for c in deck)
    assert any(c.rank == 'K' and c.suit == 'C' for c in deck)
