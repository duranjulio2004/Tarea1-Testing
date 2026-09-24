import pytest
import numpy as np
from game import MahjongGame

@pytest.fixture
def game():
    return MahjongGame(allow_step_back=True)

def test_init_game(game):
    state, current_player = game.init_game()
    assert isinstance(state, dict)
    assert 0 <= current_player < 4
    assert len(game.players) == 4
    assert len(game.history) == 0

def test_step_and_step_back(game):
    game.init_game()
    current_player_id = game.get_player_id()
    card = game.players[current_player_id].hand[0]
    
    game.step(card)
    assert len(game.history) == 1
    
    success = game.step_back()
    assert success is True
    assert game.step_back() is False

def test_get_legal_actions():
    state_play = {'valid_act': ['play'], 'action_cards': ['a', 'b', 'c']}
    assert MahjongGame.get_legal_actions(state_play) == ['a', 'b', 'c']
    
    state_other = {'valid_act': ['pong', 'chow']}
    assert MahjongGame.get_legal_actions(state_other) == ['pong', 'chow']

def test_game_utility_methods(game):
    game.init_game()
    assert game.get_num_actions() == 38
    assert game.get_num_players() == 4
    assert isinstance(game.get_player_id(), int)

def test_is_over(game):
    game.init_game()
    assert isinstance(game.is_over(), bool)

def test_round_proceed_logic_branches(game):
    game.init_game()
    # When step is called with a card, it triggers play_card and potentially updates the round.
    # The 'stand', 'gong', 'pong', 'chow' branches are conditioned on valid_act.
    # If we call 'stand' without valid_act being set correctly by logic, it falls through to
    # the 'else' (regular play) logic.
    
    # Trigger regular play logic
    game.step(game.players[game.get_player_id()].hand[0])
    
    # We test the logic flow of proceed_round.
    # The 'stand' action calls judger.judge_chow. If that returns False, it falls to the else block.
    # We call it twice to ensure no errors occur.
    game.step('stand')
    game.step('stand')

def test_get_state_branches():
    game = MahjongGame()
    game.init_game()
    
    # Regular Play branch
    game.round.valid_act = False
    state1 = game.get_state(0)
    assert state1['valid_act'] == ['play']
    
    # PONG/GONG/CHOW branch
    game.round.valid_act = 'pong'
    game.round.last_cards = ['c1']
    state2 = game.get_state(0)
    assert state2['valid_act'] == ['pong', 'stand']

def test_complex_round_flow():
    rs = np.random.RandomState(42)
    game = MahjongGame()
    game.np_random = rs
    game.init_game()
    
    current_p = game.get_player_id()
    card = game.players[current_p].hand[0]
    game.step(card)
    assert game.get_player_id() != current_p

def test_step_back_persistence(game):
    game.init_game()
    card = game.players[0].hand[0]
    game.step(card)
    game.step_back()
    assert len(game.history) == 0
