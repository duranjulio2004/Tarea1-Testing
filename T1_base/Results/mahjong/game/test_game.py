import pytest
import numpy as np
from game import MahjongGame

@pytest.fixture
def game():
    return MahjongGame(allow_step_back=True)

def test_init_game(game):
    state, player_id = game.init_game()
    assert len(game.players) == 4
    assert player_id >= 0
    assert 'valid_act' in state
    assert game.cur_state is not None

def test_step_back_flow(game):
    game.init_game()
    card = game.players[game.round.current_player].hand[0]
    game.step(card)
    assert len(game.history) == 1
    success = game.step_back()
    assert success is True
    assert len(game.history) == 0
    assert game.step_back() is False

def test_get_legal_actions():
    state_play = {'valid_act': ['play'], 'action_cards': ['c1', 'c2']}
    assert MahjongGame.get_legal_actions(state_play) == ['c1', 'c2']
    state_act = {'valid_act': ['pong', 'stand']}
    assert MahjongGame.get_legal_actions(state_act) == ['pong', 'stand']

def test_game_properties():
    game = MahjongGame()
    assert game.get_num_actions() == 38
    assert game.get_num_players() == 4
    game.init_game()
    assert game.get_player_id() == game.round.current_player

def test_is_over(game):
    game.init_game()
    assert game.is_over() is False

def test_step_logic(game):
    game.init_game()
    initial_player = game.round.current_player
    card_to_play = game.players[initial_player].hand[0]
    state, next_player = game.step(card_to_play)
    assert next_player != initial_player
    assert state['player'] == next_player

def test_step_back_disabled():
    game = MahjongGame(allow_step_back=False)
    game.init_game()
    card = game.players[game.round.current_player].hand[0]
    game.step(card)
    assert len(game.history) == 0

def test_step_back_integrity(game):
    game.init_game()
    initial_player = game.round.current_player
    card = game.players[initial_player].hand[0]
    game.step(card)
    assert game.round.current_player != initial_player
    game.step_back()
    assert game.round.current_player == initial_player

def test_get_state_branching(game):
    game.init_game()
    game.round.valid_act = 'pong'
    game.round.last_cards = ['c1']
    state = game.get_state(0)
    assert state['valid_act'] == ['pong', 'stand']
    assert state['action_cards'] == ['c1']

def test_invalid_actions_resilience(game):
    game.init_game()
    with pytest.raises(ValueError):
        game.step("invalid-card")

def test_proceed_round_branches(game):
    game.init_game()
    # Populate table so index isn't out of range
    card = game.players[0].hand[0]
    game.step(card)
    # Ensure a card is on the table
    assert len(game.dealer.table) > 0
    
    # Trigger chow/stand logic branch (stand)
    game.round.last_player = 0
    game.round.current_player = 1
    game.step('stand')
    assert game.round.valid_act in [False, 'chow']
