"""Tests for backend.app.ai.card_play — shared card-selection utilities.

These functions are used by MediumAI and HardAI — correctness bugs here
affect all non-trivial AI decision-making.
"""

import pytest

from backend.app.models import Card, Suit, Rank
from backend.app.ai.card_play import (
    would_win,
    best_winning_card,
    dump_lowest,
    lowest_winning_trump,
)


# ---------------------------------------------------------------------------
# would_win
# ---------------------------------------------------------------------------

class TestWouldWin:
    """Tests for would_win(card, trick_cards, lead_suit, trump)."""

    def test_trump_wins_when_no_trump_in_trick(self):
        """A trump card beats non-trump cards in the trick."""
        card = Card(suit=Suit.SPADES, rank=Rank.TWO)
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.HEARTS, rank=Rank.KING),
        ]
        assert would_win(card, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES) is True

    def test_trump_loses_to_higher_trump_in_trick(self):
        """A trump card loses if the trick already has a higher trump."""
        card = Card(suit=Suit.SPADES, rank=Rank.FIVE)
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.SPADES, rank=Rank.TEN),
        ]
        assert would_win(card, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES) is False

    def test_trump_wins_against_lower_trump_in_trick(self):
        """A trump card beats a lower trump already played."""
        card = Card(suit=Suit.SPADES, rank=Rank.KING)
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.SPADES, rank=Rank.SEVEN),
        ]
        assert would_win(card, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES) is True

    def test_trump_equal_rank_does_not_win(self):
        """A trump card with same rank as best trump does not win (strict >)."""
        card = Card(suit=Suit.SPADES, rank=Rank.TEN)
        trick_cards = [Card(suit=Suit.SPADES, rank=Rank.TEN)]
        assert would_win(card, trick_cards, lead_suit=Suit.SPADES, trump=Suit.SPADES) is False

    def test_lead_suit_wins_when_no_trump_in_trick(self):
        """A lead-suit card wins if it outranks all lead-suit cards and no trump present."""
        card = Card(suit=Suit.HEARTS, rank=Rank.ACE)
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.KING),
            Card(suit=Suit.CLUBS, rank=Rank.ACE),
        ]
        assert would_win(card, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES) is True

    def test_lead_suit_loses_to_trump_in_trick(self):
        """A lead-suit card loses when the trick contains a trump."""
        card = Card(suit=Suit.HEARTS, rank=Rank.ACE)
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.THREE),
            Card(suit=Suit.SPADES, rank=Rank.TWO),
        ]
        assert would_win(card, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES) is False

    def test_lead_suit_loses_to_higher_lead_suit(self):
        """A lead-suit card loses to a higher-ranked lead-suit card in the trick."""
        card = Card(suit=Suit.HEARTS, rank=Rank.JACK)
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.QUEEN)]
        assert would_win(card, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES) is False

    def test_off_suit_non_trump_never_wins(self):
        """A card that is neither trump nor lead suit never wins."""
        card = Card(suit=Suit.CLUBS, rank=Rank.ACE)
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.TWO)]
        assert would_win(card, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES) is False

    def test_empty_trick_cards_trump_wins(self):
        """With an empty trick, a trump card wins (has_trump is False, returns True)."""
        card = Card(suit=Suit.SPADES, rank=Rank.TWO)
        assert would_win(card, [], lead_suit=Suit.HEARTS, trump=Suit.SPADES) is True

    def test_empty_trick_cards_lead_suit_raises(self):
        """With an empty trick, a lead-suit card hits max() on empty sequence."""
        card = Card(suit=Suit.HEARTS, rank=Rank.ACE)
        with pytest.raises(ValueError):
            would_win(card, [], lead_suit=Suit.HEARTS, trump=Suit.SPADES)

    def test_empty_trick_cards_off_suit_returns_false(self):
        """With an empty trick, an off-suit non-trump card returns False."""
        card = Card(suit=Suit.CLUBS, rank=Rank.ACE)
        assert would_win(card, [], lead_suit=Suit.HEARTS, trump=Suit.SPADES) is False

    def test_trump_wins_against_multiple_lead_cards(self):
        """Even the lowest trump beats multiple high lead-suit cards."""
        card = Card(suit=Suit.SPADES, rank=Rank.TWO)
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.HEARTS, rank=Rank.KING),
        ]
        assert would_win(card, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES) is True

    def test_lead_suit_lower_than_best_loses(self):
        """A lead-suit card lower than the best lead-suit in trick loses."""
        card = Card(suit=Suit.HEARTS, rank=Rank.QUEEN)
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.KING)]
        assert would_win(card, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES) is False


# ---------------------------------------------------------------------------
# best_winning_card
# ---------------------------------------------------------------------------

class TestBestWinningCard:
    """Tests for best_winning_card(valid_cards, trick_cards, lead_suit, trump)."""

    def test_returns_none_when_no_card_can_win(self):
        """Returns None when none of the valid cards can beat the trick."""
        valid_cards = [
            Card(suit=Suit.CLUBS, rank=Rank.ACE),
            Card(suit=Suit.CLUBS, rank=Rank.KING),
        ]
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.TWO)]
        result = best_winning_card(valid_cards, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES)
        assert result is None

    def test_returns_none_when_trumped_and_no_higher_trump(self):
        """Returns None when trick is trumped and hand has no higher trump."""
        valid_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.DIAMONDS, rank=Rank.KING),
        ]
        trick_cards = [Card(suit=Suit.SPADES, rank=Rank.ACE)]
        result = best_winning_card(valid_cards, trick_cards, lead_suit=Suit.SPADES, trump=Suit.SPADES)
        assert result is None

    def test_prefers_lead_suit_winner_over_trump(self):
        """Returns the cheapest lead-suit winner rather than a trump winner."""
        lead_winner = Card(suit=Suit.HEARTS, rank=Rank.KING)
        trump_winner = Card(suit=Suit.SPADES, rank=Rank.TWO)
        valid_cards = [trump_winner, lead_winner]
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.JACK)]
        result = best_winning_card(valid_cards, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES)
        assert result == lead_winner

    def test_returns_lowest_rank_winner_among_lead_suit(self):
        """When multiple lead-suit cards can win, picks the lowest rank."""
        low_winner = Card(suit=Suit.HEARTS, rank=Rank.SIX)
        high_winner = Card(suit=Suit.HEARTS, rank=Rank.ACE)
        mid_winner = Card(suit=Suit.HEARTS, rank=Rank.KING)
        valid_cards = [high_winner, mid_winner, low_winner]
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.FIVE)]
        result = best_winning_card(valid_cards, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES)
        assert result == low_winner

    def test_single_card_that_can_win(self):
        """When exactly one card wins, return it."""
        winner = Card(suit=Suit.SPADES, rank=Rank.THREE)
        loser = Card(suit=Suit.CLUBS, rank=Rank.ACE)
        valid_cards = [loser, winner]
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.ACE)]
        result = best_winning_card(valid_cards, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES)
        assert result == winner

    def test_all_cards_can_win_picks_cheapest(self):
        """When all cards win, picks cheapest (lead suit first, then lowest rank)."""
        low_lead = Card(suit=Suit.HEARTS, rank=Rank.QUEEN)
        high_lead = Card(suit=Suit.HEARTS, rank=Rank.ACE)
        trump_card = Card(suit=Suit.SPADES, rank=Rank.ACE)
        valid_cards = [trump_card, high_lead, low_lead]
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.JACK)]
        result = best_winning_card(valid_cards, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES)
        assert result == low_lead

    def test_only_trump_winners_picks_lowest_trump(self):
        """When only trump cards can win, pick the lowest trump."""
        low_trump = Card(suit=Suit.SPADES, rank=Rank.FOUR)
        high_trump = Card(suit=Suit.SPADES, rank=Rank.ACE)
        valid_cards = [high_trump, low_trump]
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.SPADES, rank=Rank.THREE),
        ]
        result = best_winning_card(valid_cards, trick_cards, lead_suit=Suit.HEARTS, trump=Suit.SPADES)
        assert result == low_trump


# ---------------------------------------------------------------------------
# dump_lowest
# ---------------------------------------------------------------------------

class TestDumpLowest:
    """Tests for dump_lowest(valid_cards, trump)."""

    def test_picks_lowest_non_trump_when_available(self):
        """Picks the lowest-ranked non-trump card."""
        cards = [
            Card(suit=Suit.HEARTS, rank=Rank.KING),
            Card(suit=Suit.CLUBS, rank=Rank.THREE),
            Card(suit=Suit.SPADES, rank=Rank.TWO),
        ]
        result = dump_lowest(cards, trump=Suit.SPADES)
        assert result == Card(suit=Suit.CLUBS, rank=Rank.THREE)

    def test_picks_lowest_trump_when_only_trump(self):
        """Picks the lowest trump when all cards are trump."""
        cards = [
            Card(suit=Suit.SPADES, rank=Rank.ACE),
            Card(suit=Suit.SPADES, rank=Rank.FIVE),
            Card(suit=Suit.SPADES, rank=Rank.TWO),
        ]
        result = dump_lowest(cards, trump=Suit.SPADES)
        assert result == Card(suit=Suit.SPADES, rank=Rank.TWO)

    def test_mixed_suits_avoids_trump(self):
        """With mixed suits, avoids dumping trump even if it is the lowest card overall."""
        cards = [
            Card(suit=Suit.SPADES, rank=Rank.TWO),
            Card(suit=Suit.HEARTS, rank=Rank.TEN),
            Card(suit=Suit.DIAMONDS, rank=Rank.SEVEN),
        ]
        result = dump_lowest(cards, trump=Suit.SPADES)
        assert result == Card(suit=Suit.DIAMONDS, rank=Rank.SEVEN)

    def test_single_card_returns_that_card(self):
        """A single card is returned regardless of whether it is trump."""
        card = Card(suit=Suit.SPADES, rank=Rank.ACE)
        result = dump_lowest([card], trump=Suit.SPADES)
        assert result == card

    def test_single_non_trump_card(self):
        """A single non-trump card is returned."""
        card = Card(suit=Suit.HEARTS, rank=Rank.FIVE)
        result = dump_lowest([card], trump=Suit.SPADES)
        assert result == card

    def test_multiple_non_trump_suits_picks_lowest_across_all(self):
        """Picks the lowest rank across all non-trump suits."""
        cards = [
            Card(suit=Suit.HEARTS, rank=Rank.NINE),
            Card(suit=Suit.CLUBS, rank=Rank.FOUR),
            Card(suit=Suit.DIAMONDS, rank=Rank.SIX),
        ]
        result = dump_lowest(cards, trump=Suit.SPADES)
        assert result == Card(suit=Suit.CLUBS, rank=Rank.FOUR)

    def test_prefers_non_trump_even_when_trump_is_lower(self):
        """Non-trump is preferred even when a lower-ranked trump exists."""
        cards = [
            Card(suit=Suit.SPADES, rank=Rank.TWO),
            Card(suit=Suit.HEARTS, rank=Rank.THREE),
        ]
        result = dump_lowest(cards, trump=Suit.SPADES)
        assert result.suit == Suit.HEARTS


# ---------------------------------------------------------------------------
# lowest_winning_trump
# ---------------------------------------------------------------------------

class TestLowestWinningTrump:
    """Tests for lowest_winning_trump(valid_cards, trick_cards, trump)."""

    def test_returns_lowest_trump_that_beats_trick(self):
        """Returns the lowest trump that can beat the current trick."""
        cards = [
            Card(suit=Suit.SPADES, rank=Rank.QUEEN),
            Card(suit=Suit.SPADES, rank=Rank.FIVE),
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
        ]
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.KING)]
        result = lowest_winning_trump(cards, trick_cards, trump=Suit.SPADES)
        assert result == Card(suit=Suit.SPADES, rank=Rank.FIVE)

    def test_returns_none_when_no_trump_can_win(self):
        """Returns None when trump cards exist but cannot beat the trick."""
        cards = [
            Card(suit=Suit.SPADES, rank=Rank.THREE),
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
        ]
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.KING),
            Card(suit=Suit.SPADES, rank=Rank.JACK),
        ]
        result = lowest_winning_trump(cards, trick_cards, trump=Suit.SPADES)
        assert result is None

    def test_returns_none_when_no_trump_in_hand(self):
        """Returns None when hand has no trump cards at all."""
        cards = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.CLUBS, rank=Rank.KING),
        ]
        trick_cards = [Card(suit=Suit.HEARTS, rank=Rank.TWO)]
        result = lowest_winning_trump(cards, trick_cards, trump=Suit.SPADES)
        assert result is None

    def test_picks_lowest_of_multiple_winning_trumps(self):
        """When multiple trumps can win, picks the lowest-ranked one."""
        cards = [
            Card(suit=Suit.SPADES, rank=Rank.ACE),
            Card(suit=Suit.SPADES, rank=Rank.SIX),
            Card(suit=Suit.SPADES, rank=Rank.NINE),
        ]
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.KING),
            Card(suit=Suit.SPADES, rank=Rank.FOUR),
        ]
        result = lowest_winning_trump(cards, trick_cards, trump=Suit.SPADES)
        assert result == Card(suit=Suit.SPADES, rank=Rank.SIX)

    def test_trump_must_beat_existing_trump_in_trick(self):
        """When trick already has trump, only higher trumps qualify."""
        cards = [
            Card(suit=Suit.SPADES, rank=Rank.EIGHT),
            Card(suit=Suit.SPADES, rank=Rank.THREE),
        ]
        trick_cards = [
            Card(suit=Suit.HEARTS, rank=Rank.TWO),
            Card(suit=Suit.SPADES, rank=Rank.SEVEN),
        ]
        result = lowest_winning_trump(cards, trick_cards, trump=Suit.SPADES)
        assert result == Card(suit=Suit.SPADES, rank=Rank.EIGHT)

    def test_single_winning_trump(self):
        """When exactly one trump can win, return it."""
        cards = [
            Card(suit=Suit.SPADES, rank=Rank.KING),
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.CLUBS, rank=Rank.TEN),
        ]
        trick_cards = [Card(suit=Suit.DIAMONDS, rank=Rank.QUEEN)]
        result = lowest_winning_trump(cards, trick_cards, trump=Suit.SPADES)
        assert result == Card(suit=Suit.SPADES, rank=Rank.KING)
