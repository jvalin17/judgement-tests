import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PlayerInfo } from "./PlayerInfo";
import { SettingsProvider } from "../../context/SettingsContext";
import type { Bid } from "../../types";

function renderPlayerInfo(overrides: Partial<{
  playerId: string | null;
  playerName: string;
  bids: Bid[];
  tricksWon: Record<string, number>;
  cumulativeScores: Record<string, number>;
  isMyTurn: boolean;
}> = {}) {
  const props = {
    playerId: "p1",
    playerName: "Alice",
    bids: [],
    tricksWon: {},
    cumulativeScores: {},
    isMyTurn: false,
    ...overrides,
  };
  return render(
    <SettingsProvider>
      <PlayerInfo {...props} />
    </SettingsProvider>
  );
}

describe("PlayerInfo", () => {
  it("returns null when playerId is null", () => {
    const { container } = renderPlayerInfo({ playerId: null });
    expect(container.innerHTML).toBe("");
  });

  it("shows player name as avatar initials", () => {
    renderPlayerInfo({ playerName: "Alice" });
    // getInitials returns first 2 chars uppercased
    expect(screen.getByText("AL")).toBeInTheDocument();
  });

  it("shows cumulative score", () => {
    renderPlayerInfo({
      playerId: "p1",
      cumulativeScores: { p1: 42 },
    });
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("shows bid/tricks when bid placed", () => {
    renderPlayerInfo({
      playerId: "p1",
      bids: [{ player_id: "p1", amount: 3 }],
      tricksWon: { p1: 2 },
    });
    expect(screen.getByText("2/3")).toBeInTheDocument();
  });

  it("shows dash when no bid placed", () => {
    renderPlayerInfo({
      playerId: "p1",
      bids: [],
      tricksWon: {},
    });
    // em-dash character
    expect(screen.getByText("\u2014")).toBeInTheDocument();
  });

  it("applies active class when isMyTurn", () => {
    const { container } = renderPlayerInfo({ isMyTurn: true });
    const infoDiv = container.querySelector(".playerInfo");
    expect(infoDiv).not.toBeNull();
    expect(infoDiv!.className).toContain("playerInfoActive");
  });

  it("does not apply active class when not my turn", () => {
    const { container } = renderPlayerInfo({ isMyTurn: false });
    const infoDiv = container.querySelector(".playerInfo");
    expect(infoDiv).not.toBeNull();
    expect(infoDiv!.className).not.toContain("playerInfoActive");
  });

  it("shows avatar with correct initials for multi-word name", () => {
    renderPlayerInfo({ playerName: "Bob" });
    expect(screen.getByText("BO")).toBeInTheDocument();
  });
});
