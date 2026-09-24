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
    # Verify unique cards (suit * rank = 4 * 13 = 52)
    assert len(set(str(c) for c in deck)) == 52
    assert isinstance(deck[0], Card)

def test_blackjack_dealer_init_single_deck(rng):
    dealer = BlackjackDealer(rng, num_decks=1)
    assert len(dealer.deck) == 52
    assert dealer.num_decks == 1
    assert dealer.status == 'alive'
    assert dealer.score == 0

def test_blackjack_dealer_init_infinite_decks(rng):
    # Tests the 0 branch for infinite decks
    dealer = BlackjackDealer(rng, num_decks=0)
    assert len(dealer.deck) == 52
    assert dealer.num_decks == 0

def test_blackjack_dealer_init_multi_deck(rng):
    # Tests the multi-deck branch
    num_decks = 2
    dealer = BlackjackDealer(rng, num_decks=num_decks)
    assert len(dealer.deck) == 52 * num_decks

def test_shuffle(rng):
    dealer = BlackjackDealer(rng, num_decks=1)
    original_deck = list(dealer.deck)
    dealer.shuffle()
    # Check that deck is reordered (statistically highly likely with seed 42)
    assert dealer.deck != original_deck
    assert len(dealer.deck) == 52

def test_deal_card_finite_deck(rng):
    dealer = BlackjackDealer(rng, num_decks=1)
    player = MockPlayer()
    
    initial_len = len(dealer.deck)
    dealer.deal_card(player)
    
    assert len(player.hand) == 1
    assert len(dealer.deck) == initial_len - 1

def test_deal_card_infinite_deck(rng):
    dealer = BlackjackDealer(rng, num_decks=0)
    player = MockPlayer()
    
    initial_len = len(dealer.deck)
    dealer.deal_card(player)
    
    assert len(player.hand) == 1
    # For infinite decks (0), the card is not popped
    assert len(dealer.deck) == initial_len

def test_deal_card_persistence(rng):
    # Ensure that dealing cards keeps adding to the player's hand
    dealer = BlackjackDealer(rng, num_decks=1)
    player = MockPlayer()
    
    dealer.deal_card(player)
    dealer.deal_card(player)
    
    assert len(player.hand) == 2
    assert isinstance(player.hand[0], Card)
    assert isinstance(player.hand[1], Card)

def test_dealer_integrity_after_multiple_deals(rng):
    dealer = BlackjackDealer(rng, num_decks=1)
    player = MockPlayer()
    
    # Exhaust a small deck
    for _ in range(52):
        dealer.deal_card(player)
    
    assert len(dealer.deck) == 0
    assert len(player.hand) == 52

def test_invalid_num_decks_logic(rng):
    # Checking branch coverage for num_decks > 1
    dealer = BlackjackDealer(rng, num_decks=3)
    assert len(dealer.deck) == 52 * 3
