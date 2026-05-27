import { describe, it, expect } from "vitest";

// Re-implement clockwiseOpponents here to test the pure logic
// (the actual function lives in GameBoard.tsx as a module-private helper)

interface Player {
  id: string;
  name: string;
  player_type: string;
  ai_difficulty: string | null;
}

function clockwiseOpponents(players: Player[], humanId: string): Player[] {
  const humanIndex = players.findIndex((player) => player.id === humanId);
  if (humanIndex < 0) return players.filter((player) => player.id !== humanId);
  const result: Player[] = [];
  for (let offset = 1; offset < players.length; offset++) {
    result.push(players[(humanIndex + offset) % players.length]);
  }
  return result;
}

function makePlayers(ids: string[]): Player[] {
  return ids.map((id) => ({
    id,
    name: `Player ${id}`,
    player_type: id === "H" ? "human" : "ai",
    ai_difficulty: id === "H" ? null : "hard",
  }));
}

describe("clockwiseOpponents", () => {
  describe("3 players", () => {
    it("human at end — opponents wrap around", () => {
      const players = makePlayers(["A", "B", "H"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["A", "B"]);
    });

    it("human at start — opponents follow in order", () => {
      const players = makePlayers(["H", "A", "B"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["A", "B"]);
    });

    it("human in middle — wraps correctly", () => {
      const players = makePlayers(["A", "H", "B"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["B", "A"]);
    });
  });

  describe("4 players", () => {
    it("human at index 2 — wraps around correctly", () => {
      const players = makePlayers(["A", "B", "H", "D"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["D", "A", "B"]);
    });

    it("human at index 0 — natural order", () => {
      const players = makePlayers(["H", "A", "B", "C"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["A", "B", "C"]);
    });

    it("human at index 1 — wraps last player", () => {
      const players = makePlayers(["A", "H", "C", "D"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["C", "D", "A"]);
    });

    it("human at last index — wraps to start", () => {
      const players = makePlayers(["A", "B", "C", "H"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["A", "B", "C"]);
    });
  });

  describe("5 players", () => {
    it("human in middle of 5 — wraps correctly", () => {
      const players = makePlayers(["A", "B", "H", "D", "E"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["D", "E", "A", "B"]);
    });

    it("human at start of 5", () => {
      const players = makePlayers(["H", "A", "B", "C", "D"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["A", "B", "C", "D"]);
    });
  });

  describe("6 players", () => {
    it("human in middle of 6 — wraps correctly", () => {
      const players = makePlayers(["A", "B", "C", "H", "E", "F"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["E", "F", "A", "B", "C"]);
    });
  });

  describe("edge cases", () => {
    it("human not found — returns all others", () => {
      const players = makePlayers(["A", "B", "C"]);
      const result = clockwiseOpponents(players, "MISSING");
      expect(result.map((p) => p.id)).toEqual(["A", "B", "C"]);
    });

    it("2 players — single opponent", () => {
      const players = makePlayers(["H", "A"]);
      const result = clockwiseOpponents(players, "H");
      expect(result.map((p) => p.id)).toEqual(["A"]);
    });

    it("preserves player objects, not just ids", () => {
      const players = makePlayers(["A", "H", "B"]);
      const result = clockwiseOpponents(players, "H");
      expect(result[0].name).toBe("Player B");
      expect(result[1].name).toBe("Player A");
    });
  });
});
