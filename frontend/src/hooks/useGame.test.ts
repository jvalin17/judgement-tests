import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useGame } from "./useGame";
import { GamePhase, INITIAL_GAME_STATE, ServerEventType } from "../types";
import type { ServerEvent, Card } from "../types";

function makeEvent(type: string, data: Record<string, unknown>): ServerEvent {
  return { type: type as ServerEvent["type"], data };
}

function makeCard(suit: string, rank: number): Card {
  return { suit, rank } as Card;
}

describe("useGame", () => {
  it("initial state matches INITIAL_GAME_STATE", () => {
    const { result } = renderHook(() => useGame());
    expect(result.current.state).toEqual(INITIAL_GAME_STATE);
  });

  it("SET_GAME_INFO sets gameId and playerId", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("game-123", "player-1"));
    expect(result.current.state.gameId).toBe("game-123");
    expect(result.current.state.playerId).toBe("player-1");
  });

  it("SET_GAME_INFO transitions from LOBBY to WAITING", () => {
    const { result } = renderHook(() => useGame());
    expect(result.current.state.phase).toBe(GamePhase.LOBBY);
    act(() => result.current.setGameInfo("g1", "p1"));
    expect(result.current.state.phase).toBe(GamePhase.WAITING);
  });

  it("CONNECTED event updates all state fields", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.CONNECTED, {
          game_id: "g1",
          player_id: "p1",
          phase: "bidding",
          current_player_id: "p2",
          players: [
            { id: "p1", name: "Alice", player_type: "human", ai_difficulty: null },
            { id: "p2", name: "Bot", player_type: "ai", ai_difficulty: "easy" },
          ],
          round_number: 3,
          num_cards: 7,
          trump_suit: "hearts",
          dealer_id: "p1",
          bids: [{ player_id: "p1", amount: 2 }],
          current_trick: [],
          tricks_won: { p1: 1, p2: 0 },
          total_rounds: 10,
          must_lose_mode: false,
        }),
      ),
    );
    const state = result.current.state;
    expect(state.phase).toBe(GamePhase.BIDDING);
    expect(state.currentPlayerId).toBe("p2");
    expect(state.players).toHaveLength(2);
    expect(state.roundNumber).toBe(3);
    expect(state.numCards).toBe(7);
    expect(state.trumpSuit).toBe("hearts");
    expect(state.dealerId).toBe("p1");
    expect(state.bids).toEqual([{ player_id: "p1", amount: 2 }]);
    expect(state.tricksWon).toEqual({ p1: 1, p2: 0 });
  });

  it("ROUND_STARTED resets bids, trick, scores", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    // Set some bids first
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.CONNECTED, {
          game_id: "g1",
          player_id: "p1",
          phase: "bidding",
          current_player_id: "p1",
          players: [{ id: "p1", name: "Alice", player_type: "human", ai_difficulty: null }],
          bids: [{ player_id: "p1", amount: 3 }],
          tricks_won: { p1: 2 },
        }),
      ),
    );
    // Now start a new round
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.ROUND_STARTED, {
          round_number: 5,
          num_cards: 4,
          trump_suit: "clubs",
          dealer_id: "p1",
        }),
      ),
    );
    const state = result.current.state;
    expect(state.phase).toBe(GamePhase.BIDDING);
    expect(state.roundNumber).toBe(5);
    expect(state.numCards).toBe(4);
    expect(state.trumpSuit).toBe("clubs");
    expect(state.bids).toEqual([]);
    expect(state.currentTrick).toEqual([]);
    expect(state.tricksWon).toEqual({});
  });

  it("BID_PLACED appends to bids", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.BID_PLACED, { player_id: "p1", amount: 2 }),
      ),
    );
    expect(result.current.state.bids).toEqual([{ player_id: "p1", amount: 2 }]);
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.BID_PLACED, { player_id: "p2", amount: 0 }),
      ),
    );
    expect(result.current.state.bids).toEqual([
      { player_id: "p1", amount: 2 },
      { player_id: "p2", amount: 0 },
    ]);
  });

  it("CARD_PLAYED updates currentTrick and removes card from own hand", () => {
    const { result } = renderHook(() => useGame());
    const aceSpades = makeCard("spades", 14);
    const tenHearts = makeCard("hearts", 10);
    act(() => result.current.setGameInfo("g1", "p1"));
    // Give player a hand
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.CARDS_DEALT, { hand: [aceSpades, tenHearts] }),
      ),
    );
    expect(result.current.state.hand).toHaveLength(2);
    // Player plays ace of spades
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.CARD_PLAYED, { player_id: "p1", card: aceSpades }),
      ),
    );
    expect(result.current.state.currentTrick).toHaveLength(1);
    expect(result.current.state.currentTrick[0].card).toEqual(aceSpades);
    expect(result.current.state.hand).toHaveLength(1);
    expect(result.current.state.hand[0]).toEqual(tenHearts);
  });

  it("CARD_PLAYED does not remove card from hand when another player plays", () => {
    const { result } = renderHook(() => useGame());
    const aceSpades = makeCard("spades", 14);
    act(() => result.current.setGameInfo("g1", "p1"));
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.CARDS_DEALT, { hand: [aceSpades] }),
      ),
    );
    // Another player plays
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.CARD_PLAYED, { player_id: "p2", card: makeCard("hearts", 10) }),
      ),
    );
    expect(result.current.state.hand).toHaveLength(1);
    expect(result.current.state.hand[0]).toEqual(aceSpades);
  });

  it("TRICK_COMPLETE sets trickWinner", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.TRICK_COMPLETE, {
          winner_id: "p2",
          tricks_won: { p1: 0, p2: 1 },
        }),
      ),
    );
    expect(result.current.state.trickWinner).toBe("p2");
    expect(result.current.state.tricksWon).toEqual({ p1: 0, p2: 1 });
  });

  it("ROUND_COMPLETE updates scores and phase", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.ROUND_COMPLETE, {
          round_scores: { p1: 20, p2: -10 },
          cumulative_scores: { p1: 40, p2: 10 },
          tricks_won: { p1: 2, p2: 1 },
          bids: [
            { player_id: "p1", amount: 2 },
            { player_id: "p2", amount: 2 },
          ],
        }),
      ),
    );
    const state = result.current.state;
    expect(state.phase).toBe(GamePhase.ROUND_OVER);
    expect(state.cumulativeScores).toEqual({ p1: 40, p2: 10 });
    expect(state.roundScores).toEqual({ p1: 20, p2: -10 });
    expect(state.tricksWon).toEqual({ p1: 2, p2: 1 });
  });

  it("GAME_OVER sets phase and persona", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    const persona = {
      persona_id: "the-fox",
      persona_name: "The Fox",
      persona_category: "strategic",
      persona_tagline: "Sly and cunning",
      traits: { aggression: 0.8 },
      player_traits: { aggression: 0.7 },
    };
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.GAME_OVER, {
          final_scores: { p1: 100, p2: 50 },
          winners: ["p1"],
          persona,
        }),
      ),
    );
    const state = result.current.state;
    expect(state.phase).toBe(GamePhase.GAME_OVER);
    expect(state.cumulativeScores).toEqual({ p1: 100, p2: 50 });
    expect(state.awardedPersona).toEqual(persona);
  });

  it("GAME_OVER with null persona sets awardedPersona to null", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.GAME_OVER, {
          final_scores: { p1: 100 },
          winners: ["p1"],
          persona: null,
        }),
      ),
    );
    expect(result.current.state.awardedPersona).toBeNull();
  });

  it("events are buffered during trick winner display", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    // Set trickWinner
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.TRICK_COMPLETE, {
          winner_id: "p1",
          tricks_won: { p1: 1 },
        }),
      ),
    );
    expect(result.current.state.trickWinner).toBe("p1");
    // Now send another event — it should be buffered
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.TURN_CHANGED, { player_id: "p2", phase: "playing" }),
      ),
    );
    expect(result.current.state.pendingEvents).toHaveLength(1);
    expect(result.current.state.currentPlayerId).toBeNull(); // not applied yet
  });

  it("buffered events are replayed on clearTrick", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    // Set trickWinner
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.TRICK_COMPLETE, {
          winner_id: "p1",
          tricks_won: { p1: 1 },
        }),
      ),
    );
    // Buffer a turn change
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.TURN_CHANGED, { player_id: "p2", phase: "playing" }),
      ),
    );
    expect(result.current.state.pendingEvents).toHaveLength(1);
    // Clear trick — should replay buffered events
    act(() => result.current.clearTrick());
    expect(result.current.state.trickWinner).toBeNull();
    expect(result.current.state.currentTrick).toEqual([]);
    expect(result.current.state.pendingEvents).toEqual([]);
    expect(result.current.state.currentPlayerId).toBe("p2");
  });

  it("SET_ERROR sets error message", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setError("Something went wrong"));
    expect(result.current.state.error).toBe("Something went wrong");
  });

  it("CLEAR_ERROR clears error", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setError("oops"));
    act(() => result.current.clearError());
    expect(result.current.state.error).toBeNull();
  });

  it("RESET returns to initial state", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    act(() => result.current.resetGame());
    expect(result.current.state).toEqual(INITIAL_GAME_STATE);
  });

  it("HAND event updates hand, validCards, and validBids", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    const hand = [makeCard("spades", 14), makeCard("hearts", 10)];
    const validCards = [makeCard("spades", 14)];
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.HAND, {
          hand,
          valid_cards: validCards,
          valid_bids: [0, 1, 2],
        }),
      ),
    );
    expect(result.current.state.hand).toEqual(hand);
    expect(result.current.state.validCards).toEqual(validCards);
    expect(result.current.state.validBids).toEqual([0, 1, 2]);
  });

  it("START_TRICK_COLLECT sets trickCollecting to true", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.startTrickCollect());
    expect(result.current.state.trickCollecting).toBe(true);
  });

  it("PLAYER_JOINED adds to lobbyPlayers", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.PLAYER_JOINED, {
          player_id: "p2",
          player_name: "Bob",
          player_count: 2,
        }),
      ),
    );
    expect(result.current.state.lobbyPlayers).toEqual([
      { id: "p2", name: "Bob", isHost: false },
    ]);
  });

  it("PLAYER_JOINED does not duplicate existing player", () => {
    const { result } = renderHook(() => useGame());
    act(() => result.current.setGameInfo("g1", "p1"));
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.PLAYER_JOINED, {
          player_id: "p2",
          player_name: "Bob",
          player_count: 2,
        }),
      ),
    );
    act(() =>
      result.current.handleServerEvent(
        makeEvent(ServerEventType.PLAYER_JOINED, {
          player_id: "p2",
          player_name: "Bob",
          player_count: 2,
        }),
      ),
    );
    expect(result.current.state.lobbyPlayers).toHaveLength(1);
  });
});
