import pytest
import numpy as np
from player import MahjongPlayer
from card import MahjongCard

class MockDealer:
    def __init__(self):
        self.table = []

def test_player_initialization():
    random = np.random.RandomState(42)
    player = MahjongPlayer(1, random)
    assert player.get_player_id() == 1
    assert player.hand == []
    assert player.pile == []

def test_print_methods(capsys):
    random = np.random.RandomState(42)
    player = MahjongPlayer(1, random)
    card = MahjongCard('dots', '1')
    player.hand = [card]
    player.pile = [[card]]
    
    player.print_hand()
    captured = capsys.readouterr()
    assert "dots-1" in captured.out
    
    player.print_pile()
    captured = capsys.readouterr()
    assert "dots-1" in captured.out

def test_play_card():
    random = np.random.RandomState(42)
    player = MahjongPlayer(1, random)
    dealer = MockDealer()
    card = MahjongCard('dots', '1')
    player.hand = [card]
    
    player.play_card(dealer, card)
    assert len(player.hand) == 0
    assert dealer.table == [card]
    
    # Test ValueError when card not in hand
    with pytest.raises(ValueError):
        player.play_card(dealer, card)

def test_chow():
    random = np.random.RandomState(42)
    player = MahjongPlayer(1, random)
    dealer = MockDealer()
    # Mock last card on table
    c1 = MahjongCard('dots', '1')
    c2 = MahjongCard('dots', '2')
    c3 = MahjongCard('dots', '3')
    dealer.table = [c1]
    player.hand = [c2, c3, MahjongCard('bamboo', '1')]
    
    # Test valid chow
    chow_cards = [c2, c3]
    player.chow(dealer, chow_cards)
    assert len(player.pile) == 1
    assert player.pile[0] == chow_cards
    assert dealer.table == []  # Last card popped
    assert len(player.hand) == 1 # Bamboo-1 left
    
    # Test condition: card in hand AND card != last_card
    # Adding extra cards to hand
    player.hand = [c2, c1] 
    dealer.table = [c1]
    player.chow(dealer, [c2, c1])
    # c1 is last_card, so it shouldn't be popped from hand if it were in hand
    # The loop logic checks `if card in self.hand and card != last_card`
    assert len(player.hand) == 1 # c1 remains because it matches last_card

def test_gong():
    random = np.random.RandomState(42)
    player = MahjongPlayer(1, random)
    dealer = MockDealer()
    c1 = MahjongCard('dots', '1')
    player.hand = [c1, c1, c1, c1]
    
    gong_cards = [c1, c1, c1, c1]
    player.gong(dealer, gong_cards)
    assert len(player.pile) == 1
    assert len(player.hand) == 0

def test_pong():
    random = np.random.RandomState(42)
    player = MahjongPlayer(1, random)
    dealer = MockDealer()
    c1 = MahjongCard('dots', '1')
    player.hand = [c1, c1, c1]
    
    pong_cards = [c1, c1, c1]
    player.pong(dealer, pong_cards)
    assert len(player.pile) == 1
    assert len(player.hand) == 0

def test_actions_branching():
    # Testing the if card in self.hand logic for pong/gong/chow
    random = np.random.RandomState(42)
    player = MahjongPlayer(1, random)
    dealer = MockDealer()
    c1 = MahjongCard('dots', '1')
    c2 = MahjongCard('dots', '2')
    
    # Pong card not in hand
    player.hand = [c1]
    player.pong(dealer, [c2, c2, c2])
    assert len(player.hand) == 1
    assert len(player.pile) == 1
    
    # Gong card not in hand
    player.gong(dealer, [c2, c2, c2, c2])
    assert len(player.pile) == 2
