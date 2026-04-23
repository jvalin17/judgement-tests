from backend.app.models import Bid
from backend.app.game.scorer import score_round


def test_bid_zero_met():
    bids = [Bid(player_id="p1", amount=0)]
    assert score_round(bids, {"p1": 0}) == {"p1": 10}


def test_bid_zero_missed():
    bids = [Bid(player_id="p1", amount=0)]
    assert score_round(bids, {"p1": 2}) == {"p1": -10}


def test_bid_one_met():
    bids = [Bid(player_id="p1", amount=1)]
    assert score_round(bids, {"p1": 1}) == {"p1": 11}


def test_bid_one_missed():
    bids = [Bid(player_id="p1", amount=1)]
    assert score_round(bids, {"p1": 0}) == {"p1": -11}


def test_bid_high_met():
    bids = [Bid(player_id="p1", amount=5)]
    assert score_round(bids, {"p1": 5}) == {"p1": 50}


def test_bid_high_missed():
    bids = [Bid(player_id="p1", amount=3)]
    assert score_round(bids, {"p1": 2}) == {"p1": -30}


def test_multiple_players():
    bids = [
        Bid(player_id="p1", amount=2),
        Bid(player_id="p2", amount=0),
        Bid(player_id="p3", amount=1),
    ]
    tricks_won = {"p1": 2, "p2": 1, "p3": 1}
    scores = score_round(bids, tricks_won)
    assert scores == {"p1": 20, "p2": -10, "p3": 11}
