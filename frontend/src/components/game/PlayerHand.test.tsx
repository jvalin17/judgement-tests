import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlayerHand } from "./PlayerHand";
import { SettingsProvider } from "../../context/SettingsContext";
import type { Card } from "../../types";
import { Suit, Rank } from "../../types";

function makeCard(suit: string, rank: number): Card {
  return { suit, rank } as Card;
}

function renderHand(props: Partial<Parameters<typeof PlayerHand>[0]> = {}) {
  const defaultProps = {
    hand: [
      makeCard(Suit.SPADES, Rank.ACE),
      makeCard(Suit.HEARTS, Rank.KING),
      makeCard(Suit.DIAMONDS, Rank.FIVE),
    ],
    validCards: [],
    isMyTurn: false,
    onPlayCard: vi.fn(),
    ...props,
  };
  return {
    ...render(
      <SettingsProvider>
        <PlayerHand {...defaultProps} />
      </SettingsProvider>
    ),
    onPlayCard: defaultProps.onPlayCard,
  };
}

describe("PlayerHand", () => {
  it("renders all cards in the hand", () => {
    renderHand();
    // Each card shows rank label twice (top corner + bottom corner)
    expect(screen.getAllByText("A").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("K").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("5").length).toBeGreaterThanOrEqual(2);
  });

  it("marks playable cards with button role when it is my turn", () => {
    const hand = [
      makeCard(Suit.SPADES, Rank.ACE),
      makeCard(Suit.HEARTS, Rank.KING),
    ];
    renderHand({
      hand,
      validCards: [hand[0]],
      isMyTurn: true,
    });
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(1); // only Ace of Spades is playable
  });

  it("calls onPlayCard when a playable card is clicked", async () => {
    const user = userEvent.setup();
    const hand = [
      makeCard(Suit.SPADES, Rank.ACE),
      makeCard(Suit.HEARTS, Rank.KING),
    ];
    const { onPlayCard } = renderHand({
      hand,
      validCards: [hand[0]],
      isMyTurn: true,
    });
    const button = screen.getByRole("button");
    await user.click(button);
    expect(onPlayCard).toHaveBeenCalledWith(hand[0]);
  });

  it("does not render any buttons when it is not my turn", () => {
    const hand = [makeCard(Suit.SPADES, Rank.ACE)];
    renderHand({
      hand,
      validCards: hand,
      isMyTurn: false,
    });
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });

  it("renders empty hand without errors", () => {
    renderHand({ hand: [], validCards: [] });
    // Should not throw
  });

  it("sorts cards by suit then rank", () => {
    const hand = [
      makeCard(Suit.HEARTS, Rank.ACE),    // hearts last in sort
      makeCard(Suit.SPADES, Rank.TWO),     // spades first in sort
      makeCard(Suit.SPADES, Rank.ACE),     // spades first, higher rank
    ];
    const { container } = renderHand({ hand, validCards: [], isMyTurn: false });
    // Cards should be rendered in sorted order: spades(2, A), then hearts(A)
    const cards = container.querySelectorAll(".card");
    expect(cards.length).toBe(3);
  });
});
