"""Tests for deck creation, shuffling, and dealing.

Verifies the foundation that all other game logic depends on:
52 unique cards, correct distribution, no duplicates across hands.
"""

import random

from backend.app.models import Suit, Rank
from backend.app.game.deck import create_deck, shuffle_deck, deal


class TestCreateDeck:
    def test_has_52_cards(self):
        deck = create_deck()
        assert len(deck) == 52

    def test_all_cards_unique(self):
        deck = create_deck()
        tuples = [(card.suit, card.rank) for card in deck]
        assert len(set(tuples)) == 52

    def test_four_suits_thirteen_ranks(self):
        deck = create_deck()
        suits = {card.suit for card in deck}
        ranks = {card.rank for card in deck}
        assert suits == {Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS}
        assert len(ranks) == 13


class TestShuffleDeck:
    def test_preserves_all_cards(self):
        deck = create_deck()
        shuffled = shuffle_deck(deck)
        assert sorted(deck, key=lambda c: (c.suit.value, c.rank.value)) == \
               sorted(shuffled, key=lambda c: (c.suit.value, c.rank.value))

    def test_seeded_shuffle_is_deterministic(self):
        deck = create_deck()
        shuffled_a = shuffle_deck(deck, rng=random.Random(42))
        shuffled_b = shuffle_deck(deck, rng=random.Random(42))
        assert shuffled_a == shuffled_b

    def test_does_not_mutate_original(self):
        deck = create_deck()
        original = list(deck)
        shuffle_deck(deck)
        assert deck == original


class TestDeal:
    def test_correct_hand_sizes(self):
        deck = create_deck()
        hands = deal(deck, num_players=4, cards_per_player=10)
        assert len(hands) == 4
        assert all(len(hand) == 10 for hand in hands)

    def test_no_duplicate_cards_across_hands(self):
        deck = shuffle_deck(create_deck())
        hands = deal(deck, num_players=3, cards_per_player=10)
        all_cards = [card for hand in hands for card in hand]
        tuples = [(card.suit, card.rank) for card in all_cards]
        assert len(set(tuples)) == 30

    def test_deal_one_card_each(self):
        deck = create_deck()
        hands = deal(deck, num_players=5, cards_per_player=1)
        assert len(hands) == 5
        assert all(len(hand) == 1 for hand in hands)
