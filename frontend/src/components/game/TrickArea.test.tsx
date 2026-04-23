import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { TrickArea } from "./TrickArea";
import { makePlayer, makeCard } from "../../test/helpers";
import { SettingsProvider } from "../../context/SettingsContext";
import type { TrickPlay, Player } from "../../types";

const players = [
  makePlayer({ id: "p1", name: "Alice" }),
  makePlayer({ id: "p2", name: "Bob" }),
  makePlayer({ id: "p3", name: "Charlie" }),
];

const seatPositions = [
  { left: "50%", top: "80%" },
  { left: "15%", top: "30%" },
  { left: "85%", top: "30%" },
];

function renderTrickArea(overrides: Partial<{
  currentTrick: TrickPlay[];
  players: Player[];
  orderedPlayers: Player[];
  seatPositions: { left: string; top: string }[];
  trickWinner: string | null;
  trickCollecting: boolean;
}> = {}) {
  const props = {
    currentTrick: [],
    players,
    orderedPlayers: players,
    seatPositions,
    trickWinner: null,
    trickCollecting: false,
    ...overrides,
  };
  return render(
    <SettingsProvider>
      <TrickArea {...props} />
    </SettingsProvider>
  );
}

describe("TrickArea", () => {
  it("shows waiting message when no cards played and no winner", () => {
    renderTrickArea({ currentTrick: [], trickWinner: null });
    expect(screen.getByText("Waiting for play...")).toBeInTheDocument();
  });

  it("renders cards for each play in currentTrick", () => {
    const trick: TrickPlay[] = [
      { player_id: "p1", card: makeCard("spades", "14") },
      { player_id: "p2", card: makeCard("hearts", "10") },
    ];
    renderTrickArea({ currentTrick: trick });
    // Each card slot renders the player name
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("shows player names for each trick card", () => {
    const trick: TrickPlay[] = [
      { player_id: "p1", card: makeCard("clubs", "7") },
      { player_id: "p2", card: makeCard("diamonds", "12") },
      { player_id: "p3", card: makeCard("spades", "3") },
    ];
    renderTrickArea({ currentTrick: trick });
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("Charlie")).toBeInTheDocument();
  });

  it("shows lead badge for first card only", () => {
    const trick: TrickPlay[] = [
      { player_id: "p1", card: makeCard("spades", "14") },
      { player_id: "p2", card: makeCard("hearts", "10") },
    ];
    const { container } = renderTrickArea({ currentTrick: trick });
    const leadBadges = container.querySelectorAll(".leadCardBadge");
    expect(leadBadges).toHaveLength(1);
    expect(leadBadges[0].textContent).toBe("\u2605");
  });

  it("shows winner banner with player name when trickWinner set", () => {
    const trick: TrickPlay[] = [
      { player_id: "p1", card: makeCard("spades", "14") },
      { player_id: "p2", card: makeCard("hearts", "10") },
    ];
    renderTrickArea({ currentTrick: trick, trickWinner: "p1" });
    expect(screen.getByText("Alice wins!")).toBeInTheDocument();
  });

  it("shows no winner banner when trickCollecting", () => {
    const trick: TrickPlay[] = [
      { player_id: "p1", card: makeCard("spades", "14") },
      { player_id: "p2", card: makeCard("hearts", "10") },
    ];
    renderTrickArea({ currentTrick: trick, trickWinner: "p1", trickCollecting: true });
    expect(screen.queryByText("Alice wins!")).not.toBeInTheDocument();
  });

  it("applies collect animation class when trickCollecting", () => {
    const trick: TrickPlay[] = [
      { player_id: "p1", card: makeCard("spades", "14") },
    ];
    const { container } = renderTrickArea({
      currentTrick: trick,
      trickWinner: "p1",
      trickCollecting: true,
    });
    const pile = container.querySelector(".trickPile");
    expect(pile).not.toBeNull();
    expect(pile!.className).toContain("collectTrick");
  });
});
