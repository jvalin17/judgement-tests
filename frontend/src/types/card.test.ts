import { describe, it, expect } from "vitest";
import {
  Suit,
  Rank,
  SUIT_SYMBOLS,
  SUIT_COLORS,
  RANK_DISPLAY,
  TRUMP_ORDER,
  isSameCard,
  cardDisplayName,
} from "./card";
import type { Card } from "./card";

describe("SUIT_SYMBOLS", () => {
  it("maps spades to ♠", () => {
    expect(SUIT_SYMBOLS[Suit.SPADES]).toBe("♠");
  });

  it("maps diamonds to ♦", () => {
    expect(SUIT_SYMBOLS[Suit.DIAMONDS]).toBe("♦");
  });

  it("maps clubs to ♣", () => {
    expect(SUIT_SYMBOLS[Suit.CLUBS]).toBe("♣");
  });

  it("maps hearts to ♥", () => {
    expect(SUIT_SYMBOLS[Suit.HEARTS]).toBe("♥");
  });

  it("has exactly 4 entries", () => {
    expect(Object.keys(SUIT_SYMBOLS)).toHaveLength(4);
  });
});

describe("SUIT_COLORS", () => {
  it("spades are black", () => {
    expect(SUIT_COLORS[Suit.SPADES]).toBe("black");
  });

  it("clubs are black", () => {
    expect(SUIT_COLORS[Suit.CLUBS]).toBe("black");
  });

  it("hearts are red", () => {
    expect(SUIT_COLORS[Suit.HEARTS]).toBe("red");
  });

  it("diamonds are red", () => {
    expect(SUIT_COLORS[Suit.DIAMONDS]).toBe("red");
  });
});

describe("RANK_DISPLAY", () => {
  it("maps all 13 ranks", () => {
    expect(Object.keys(RANK_DISPLAY)).toHaveLength(13);
  });

  it("maps numeric ranks correctly", () => {
    expect(RANK_DISPLAY[Rank.TWO]).toBe("2");
    expect(RANK_DISPLAY[Rank.THREE]).toBe("3");
    expect(RANK_DISPLAY[Rank.FOUR]).toBe("4");
    expect(RANK_DISPLAY[Rank.FIVE]).toBe("5");
    expect(RANK_DISPLAY[Rank.SIX]).toBe("6");
    expect(RANK_DISPLAY[Rank.SEVEN]).toBe("7");
    expect(RANK_DISPLAY[Rank.EIGHT]).toBe("8");
    expect(RANK_DISPLAY[Rank.NINE]).toBe("9");
    expect(RANK_DISPLAY[Rank.TEN]).toBe("10");
  });

  it("maps face cards correctly", () => {
    expect(RANK_DISPLAY[Rank.JACK]).toBe("J");
    expect(RANK_DISPLAY[Rank.QUEEN]).toBe("Q");
    expect(RANK_DISPLAY[Rank.KING]).toBe("K");
    expect(RANK_DISPLAY[Rank.ACE]).toBe("A");
  });
});

describe("TRUMP_ORDER", () => {
  it("has 4 suits in the correct order", () => {
    expect(TRUMP_ORDER).toEqual([
      Suit.SPADES,
      Suit.DIAMONDS,
      Suit.CLUBS,
      Suit.HEARTS,
    ]);
  });
});

describe("isSameCard", () => {
  it("returns true for identical cards", () => {
    const card: Card = { suit: Suit.SPADES, rank: Rank.ACE };
    expect(isSameCard(card, { suit: Suit.SPADES, rank: Rank.ACE })).toBe(true);
  });

  it("returns false when suits differ", () => {
    const cardA: Card = { suit: Suit.SPADES, rank: Rank.ACE };
    const cardB: Card = { suit: Suit.HEARTS, rank: Rank.ACE };
    expect(isSameCard(cardA, cardB)).toBe(false);
  });

  it("returns false when ranks differ", () => {
    const cardA: Card = { suit: Suit.SPADES, rank: Rank.ACE };
    const cardB: Card = { suit: Suit.SPADES, rank: Rank.KING };
    expect(isSameCard(cardA, cardB)).toBe(false);
  });

  it("returns false when both differ", () => {
    const cardA: Card = { suit: Suit.SPADES, rank: Rank.ACE };
    const cardB: Card = { suit: Suit.HEARTS, rank: Rank.TWO };
    expect(isSameCard(cardA, cardB)).toBe(false);
  });
});

describe("cardDisplayName", () => {
  it("formats Ace of Spades as A♠", () => {
    expect(cardDisplayName({ suit: Suit.SPADES, rank: Rank.ACE })).toBe("A♠");
  });

  it("formats 10 of Clubs as 10♣", () => {
    expect(cardDisplayName({ suit: Suit.CLUBS, rank: Rank.TEN })).toBe("10♣");
  });

  it("formats Queen of Hearts as Q♥", () => {
    expect(cardDisplayName({ suit: Suit.HEARTS, rank: Rank.QUEEN })).toBe("Q♥");
  });

  it("formats 2 of Diamonds as 2♦", () => {
    expect(cardDisplayName({ suit: Suit.DIAMONDS, rank: Rank.TWO })).toBe("2♦");
  });
});
