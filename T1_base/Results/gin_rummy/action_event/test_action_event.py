import pytest
import numpy as np
from gin_rummy import Card
import utils
from action_event import (
    ActionEvent, ScoreNorthPlayerAction, ScoreSouthPlayerAction,
    DrawCardAction, PickUpDiscardAction, DeclareDeadHandAction,
    GinAction, DiscardAction, KnockAction,
    score_player_0_action_id, score_player_1_action_id,
    draw_card_action_id, pick_up_discard_action_id,
    declare_dead_hand_action_id, gin_action_id,
    discard_action_id, knock_action_id
)

def test_action_event_base():
    a1 = ActionEvent(0)
    a2 = ActionEvent(0)
    a3 = ActionEvent(1)
    assert a1 == a2
    assert a1 != a3
    assert a1 != "not an action"
    assert ActionEvent.get_num_actions() == knock_action_id + 52

def test_decode_action_valid():
    assert isinstance(ActionEvent.decode_action(score_player_0_action_id), ScoreNorthPlayerAction)
    assert isinstance(ActionEvent.decode_action(score_player_1_action_id), ScoreSouthPlayerAction)
    assert isinstance(ActionEvent.decode_action(draw_card_action_id), DrawCardAction)
    assert isinstance(ActionEvent.decode_action(pick_up_discard_action_id), PickUpDiscardAction)
    assert isinstance(ActionEvent.decode_action(declare_dead_hand_action_id), DeclareDeadHandAction)
    assert isinstance(ActionEvent.decode_action(gin_action_id), GinAction)

def test_decode_action_discard_knock():
    # Test boundary and mid for DiscardAction (6 to 57)
    d_start = ActionEvent.decode_action(discard_action_id)
    assert isinstance(d_start, DiscardAction)
    assert d_start.action_id == discard_action_id
    
    d_end = ActionEvent.decode_action(discard_action_id + 51)
    assert isinstance(d_end, DiscardAction)
    
    # Test boundary and mid for KnockAction (58 to 109)
    k_start = ActionEvent.decode_action(knock_action_id)
    assert isinstance(k_start, KnockAction)
    assert k_start.action_id == knock_action_id
    
    k_end = ActionEvent.decode_action(knock_action_id + 51)
    assert isinstance(k_end, KnockAction)

def test_decode_action_invalid():
    with pytest.raises(Exception, match="decode_action: unknown action_id=-1"):
        ActionEvent.decode_action(-1)
    with pytest.raises(Exception, match="decode_action: unknown action_id=200"):
        ActionEvent.decode_action(200)

def test_action_strings():
    card = Card('S', 'A')
    assert str(ScoreNorthPlayerAction()) == "score N"
    assert str(ScoreSouthPlayerAction()) == "score S"
    assert str(DrawCardAction()) == "draw_card"
    assert str(PickUpDiscardAction()) == "pick_up_discard"
    assert str(DeclareDeadHandAction()) == "declare_dead_hand"
    assert str(GinAction()) == "gin"
    assert str(DiscardAction(card)) == "discard AS"
    assert str(KnockAction(card)) == "knock AS"

def test_action_subclass_initialization():
    card = Card('H', 'K')
    d = DiscardAction(card)
    assert d.card == card
    assert d.action_id == discard_action_id + utils.get_card_id(card)
    
    k = KnockAction(card)
    assert k.card == card
    assert k.action_id == knock_action_id + utils.get_card_id(card)

def test_action_eq_logic():
    card1 = Card('S', 'A')
    card2 = Card('H', 'K')
    assert DiscardAction(card1) == DiscardAction(card1)
    assert DiscardAction(card1) != DiscardAction(card2)
    assert KnockAction(card1) == KnockAction(card1)
    assert KnockAction(card1) != KnockAction(card2)
    assert DiscardAction(card1) != KnockAction(card1)
