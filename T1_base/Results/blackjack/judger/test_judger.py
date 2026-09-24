import pytest
import numpy as np
from judger import BlackjackJudger
from base import Card

class MockPlayer:
    def __init__(self, hand, status=None, score=None):
        self.hand = hand
        self.status = status
        self.score = score

class MockGame:
    def __init__(self, players, dealer):
        self.players = players
        self.dealer = dealer
        self.winner = {}

@pytest.fixture
def judger():
    np_random = np.random.RandomState(42)
    return BlackjackJudger(np_random)

def test_judge_score_basic():
    np_random = np.random.RandomState(42)
    j = BlackjackJudger(np_random)
    
    # Normal cards
    cards = [Card('S', '2'), Card('H', '3')]
    assert j.judge_score(cards) == 5
    
    # Face cards
    cards = [Card('S', 'K'), Card('H', 'T')]
    assert j.judge_score(cards) == 20
    
    # Ace adjustment (high to low)
    cards = [Card('S', 'A'), Card('H', 'A'), Card('C', '9')] # 11+11+9 = 31 -> 21
    assert j.judge_score(cards) == 21
    
    # Multiple aces
    cards = [Card('S', 'A'), Card('H', 'A'), Card('C', 'A')] # 11+1+1 = 13
    assert j.judge_score(cards) == 13

def test_judge_round():
    j = BlackjackJudger(np.random.RandomState(42))
    
    # Alive
    p_alive = MockPlayer([Card('S', '5'), Card('H', '6')])
    status, score = j.judge_round(p_alive)
    assert status == "alive"
    assert score == 11
    
    # Bust
    p_bust = MockPlayer([Card('S', 'K'), Card('H', 'Q'), Card('D', '5')])
    status, score = j.judge_round(p_bust)
    assert status == "bust"
    assert score == 25

def test_judge_game():
    j = BlackjackJudger(np.random.RandomState(42))
    
    # Player bust
    p1 = MockPlayer([], status='bust')
    d = MockPlayer([], status='alive', score=15)
    game = MockGame([p1], d)
    j.judge_game(game, 0)
    assert game.winner['player0'] == -1
    
    # Dealer bust, player alive
    p2 = MockPlayer([], status='alive', score=15)
    d = MockPlayer([], status='bust', score=22)
    game = MockGame([p2], d)
    j.judge_game(game, 0)
    assert game.winner['player0'] == 2
    
    # Player score > dealer
    p3 = MockPlayer([], status='alive', score=20)
    d = MockPlayer([], status='alive', score=18)
    game = MockGame([p3], d)
    j.judge_game(game, 0)
    assert game.winner['player0'] == 2
    
    # Player score < dealer
    p4 = MockPlayer([], status='alive', score=15)
    d = MockPlayer([], status='alive', score=19)
    game = MockGame([p4], d)
    j.judge_game(game, 0)
    assert game.winner['player0'] == -1
    
    # Tie
    p5 = MockPlayer([], status='alive', score=17)
    d = MockPlayer([], status='alive', score=17)
    game = MockGame([p5], d)
    j.judge_game(game, 0)
    assert game.winner['player0'] == 1

def test_judge_score_empty_list():
    j = BlackjackJudger(np.random.RandomState(42))
    assert j.judge_score([]) == 0

def test_judge_score_boundary_ace_logic():
    j = BlackjackJudger(np.random.RandomState(42))
    # 21 should not decrease
    cards = [Card('S', 'A'), Card('C', 'T')]
    assert j.judge_score(cards) == 21
    # 22 should decrease
    cards = [Card('S', 'A'), Card('C', 'T'), Card('H', 'A')]
    assert j.judge_score(cards) == 12
