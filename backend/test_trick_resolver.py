from backend.app.models import Card, Suit, Rank, Trick, TrickPlay
from backend.app.game.trick_resolver import resolve_trick


def _trick(plays: list[tuple[str, Suit, Rank]]) -> Trick:
    return Trick(
        plays=[TrickPlay(player_id=pid, card=Card(suit=s, rank=r)) for pid, s, r in plays],
        lead_suit=plays[0][1] if plays else None,
    )


def test_highest_of_lead_suit_wins():
    trick = _trick([
        ("p1", Suit.HEARTS, Rank.FIVE),
        ("p2", Suit.HEARTS, Rank.TEN),
        ("p3", Suit.HEARTS, Rank.THREE),
    ])
    assert resolve_trick(trick, Suit.SPADES) == "p2"


def test_trump_beats_lead_suit():
    trick = _trick([
        ("p1", Suit.HEARTS, Rank.ACE),
        ("p2", Suit.SPADES, Rank.TWO),
        ("p3", Suit.HEARTS, Rank.KING),
    ])
    assert resolve_trick(trick, Suit.SPADES) == "p2"


def test_higher_trump_beats_lower_trump():
    trick = _trick([
        ("p1", Suit.HEARTS, Rank.ACE),
        ("p2", Suit.SPADES, Rank.TWO),
        ("p3", Suit.SPADES, Rank.SEVEN),
    ])
    assert resolve_trick(trick, Suit.SPADES) == "p3"


def test_off_suit_non_trump_loses():
    trick = _trick([
        ("p1", Suit.HEARTS, Rank.THREE),
        ("p2", Suit.CLUBS, Rank.ACE),
        ("p3", Suit.HEARTS, Rank.FIVE),
    ])
    assert resolve_trick(trick, Suit.SPADES) == "p3"


def test_lead_suit_is_trump():
    trick = _trick([
        ("p1", Suit.SPADES, Rank.THREE),
        ("p2", Suit.SPADES, Rank.ACE),
        ("p3", Suit.HEARTS, Rank.ACE),
    ])
    assert resolve_trick(trick, Suit.SPADES) == "p2"


def test_single_card_trick():
    trick = _trick([("p1", Suit.HEARTS, Rank.FIVE)])
    assert resolve_trick(trick, Suit.SPADES) == "p1"
