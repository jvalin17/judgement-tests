import { describe, it, expect, vi, beforeEach } from "vitest";

// We need to import after mocking fetch
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Dynamic import so fetch is already stubbed
const api = await import("./api");

function jsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as Response);
}

function errorResponse(status: number, detail?: string) {
  const body = detail ? { detail } : {};
  return Promise.resolve({
    ok: false,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response);
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("createGame", () => {
  it("sends POST with correct body and returns response", async () => {
    const responseData = { game_id: "g1", player_ids: { Alice: "p1" } };
    mockFetch.mockReturnValue(jsonResponse(responseData));

    const result = await api.createGame({
      variant: "10_to_1" as any,
      must_lose_mode: false,
      players: [{ name: "Alice", is_ai: false, ai_difficulty: null }],
    });

    expect(result.game_id).toBe("g1");
    expect(mockFetch).toHaveBeenCalledWith("/api/games", expect.objectContaining({
      method: "POST",
      headers: { "Content-Type": "application/json" },
    }));
  });

  it("throws ApiError on failure with detail message", async () => {
    mockFetch.mockReturnValue(errorResponse(400, "Duplicate names"));

    await expect(api.createGame({
      variant: "10_to_1" as any,
      must_lose_mode: false,
      players: [],
    })).rejects.toThrow("Duplicate names");
  });
});

describe("getGameState", () => {
  it("fetches game state by id", async () => {
    const state = { game_id: "g1", phase: "bidding", players: [] };
    mockFetch.mockReturnValue(jsonResponse(state));

    const result = await api.getGameState("g1");
    expect(result.game_id).toBe("g1");
    expect(mockFetch).toHaveBeenCalledWith("/api/games/g1");
  });
});

describe("getPlayerHand", () => {
  it("fetches hand for player", async () => {
    const hand = { hand: [], valid_cards: [], valid_bids: [0, 1] };
    mockFetch.mockReturnValue(jsonResponse(hand));

    const result = await api.getPlayerHand("g1", "p1");
    expect(result.valid_bids).toEqual([0, 1]);
    expect(mockFetch).toHaveBeenCalledWith("/api/games/g1/hand/p1");
  });
});

describe("placeBid", () => {
  it("sends bid as POST", async () => {
    mockFetch.mockReturnValue(jsonResponse({ success: true, message: "ok" }));

    const result = await api.placeBid("g1", "p1", 3);
    expect(result.success).toBe(true);
    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(callBody).toEqual({ player_id: "p1", amount: 3 });
  });
});

describe("playCard", () => {
  it("sends card suit and rank", async () => {
    mockFetch.mockReturnValue(jsonResponse({ success: true, message: "ok" }));

    await api.playCard("g1", "p1", { suit: "hearts", rank: "ace" } as any);
    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(callBody).toEqual({ player_id: "p1", suit: "hearts", rank: "ace" });
  });
});

describe("getSessionLog", () => {
  it("fetches session log", async () => {
    const log = { game_id: "g1", players: [], variant: "10_to_1", rounds: [], final_scores: {}, winners: [] };
    mockFetch.mockReturnValue(jsonResponse(log));

    const result = await api.getSessionLog("g1");
    expect(result.game_id).toBe("g1");
  });
});

describe("joinGame", () => {
  it("sends player name in body", async () => {
    mockFetch.mockReturnValue(jsonResponse({ player_id: "p2", game_id: "g1" }));

    const result = await api.joinGame("g1", "Bob");
    expect(result.player_id).toBe("p2");
    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(callBody).toEqual({ player_name: "Bob" });
  });
});

describe("startGame", () => {
  it("sends POST with player_id in query", async () => {
    mockFetch.mockReturnValue(jsonResponse({ success: true, message: "started" }));

    await api.startGame("g1", "p1");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/games/g1/start?player_id=p1",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("getLobbyList", () => {
  it("fetches from /api/lobby", async () => {
    mockFetch.mockReturnValue(jsonResponse({ games: [] }));

    const result = await api.getLobbyList();
    expect(result.games).toEqual([]);
    expect(mockFetch).toHaveBeenCalledWith("/api/lobby");
  });
});

describe("quickJoin", () => {
  it("sends player name", async () => {
    mockFetch.mockReturnValue(jsonResponse({ player_id: "p1", game_id: "g1" }));

    await api.quickJoin("Alice");
    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(callBody).toEqual({ player_name: "Alice" });
  });

  it("includes variant when provided", async () => {
    mockFetch.mockReturnValue(jsonResponse({ player_id: "p1", game_id: "g1" }));

    await api.quickJoin("Alice", "8_down_up");
    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(callBody).toEqual({ player_name: "Alice", variant: "8_down_up" });
  });
});

describe("getLobbyState", () => {
  it("fetches lobby state for game", async () => {
    const state = { game_id: "g1", phase: "lobby", variant: "10_to_1", must_lose_mode: false, players: [], host_player_id: "p1", max_players: 5 };
    mockFetch.mockReturnValue(jsonResponse(state));

    const result = await api.getLobbyState("g1");
    expect(result.host_player_id).toBe("p1");
  });
});

describe("error handling", () => {
  it("uses friendly fallback for 404", async () => {
    mockFetch.mockReturnValue(errorResponse(404));

    await expect(api.getGameState("fake")).rejects.toThrow("Room not found");
  });

  it("uses friendly fallback for 500", async () => {
    mockFetch.mockReturnValue(errorResponse(500));

    await expect(api.getGameState("fake")).rejects.toThrow("Server error");
  });

  it("uses detail from response body when available", async () => {
    mockFetch.mockReturnValue(errorResponse(400, "Game is full"));

    await expect(api.joinGame("g1", "Bob")).rejects.toThrow("Game is full");
  });

  it("uses generic fallback for unknown status", async () => {
    mockFetch.mockReturnValue(errorResponse(418));

    await expect(api.getGameState("fake")).rejects.toThrow("Something went wrong");
  });

  it("handles non-JSON error body gracefully", async () => {
    mockFetch.mockReturnValue(Promise.resolve({
      ok: false,
      status: 400,
      text: () => Promise.resolve("not json at all"),
    } as Response));

    await expect(api.getGameState("fake")).rejects.toThrow("Something went wrong with that request");
  });
});

describe("update API", () => {
  it("getVersion fetches from correct endpoint", async () => {
    mockFetch.mockReturnValue(jsonResponse({ git_sha: "abc123", build_date: null }));
    const result = await api.getVersion();
    expect(result.git_sha).toBe("abc123");
    expect(mockFetch).toHaveBeenCalledWith("/api/update/version");
  });

  it("checkForUpdate fetches update info", async () => {
    mockFetch.mockReturnValue(jsonResponse({ update_available: true, current_sha: "a", latest_sha: "b", latest_message: null, ci_status: null, error: null }));
    const result = await api.checkForUpdate();
    expect(result.update_available).toBe(true);
  });

  it("applyUpdate sends POST", async () => {
    mockFetch.mockReturnValue(jsonResponse({ success: true, message: "ok" }));
    const result = await api.applyUpdate();
    expect(result.success).toBe(true);
    expect(mockFetch).toHaveBeenCalledWith("/api/update/apply", expect.objectContaining({ method: "POST" }));
  });

  it("getUpdateStatus fetches status", async () => {
    mockFetch.mockReturnValue(jsonResponse({ state: "idle", message: "", before_sha: null, after_sha: null, log_path: null }));
    const result = await api.getUpdateStatus();
    expect(result.state).toBe("idle");
  });
});

describe("data sharing API", () => {
  it("getSharePreview fetches preview", async () => {
    mockFetch.mockReturnValue(jsonResponse({ bid_decisions: 10, play_decisions: 20, human_bid_decisions: 5, human_play_decisions: 10, total: 30, description: "test" }));
    const result = await api.getSharePreview();
    expect(result.total).toBe(30);
  });

  it("shareData sends POST", async () => {
    mockFetch.mockReturnValue(jsonResponse({ success: true, message: "shared" }));
    const result = await api.shareData();
    expect(result.success).toBe(true);
  });

  it("getShareStatus fetches status", async () => {
    mockFetch.mockReturnValue(jsonResponse({ state: "idle", message: "" }));
    const result = await api.getShareStatus();
    expect(result.state).toBe("idle");
  });

  it("checkCommunityData fetches availability", async () => {
    mockFetch.mockReturnValue(jsonResponse({ available: true, bid_size: 100, play_size: 200, updated_at: null, error: null }));
    const result = await api.checkCommunityData();
    expect(result.available).toBe(true);
  });

  it("downloadCommunityData sends POST", async () => {
    mockFetch.mockReturnValue(jsonResponse({ success: true, message: "downloaded", examples_added: 50 }));
    const result = await api.downloadCommunityData();
    expect(result.examples_added).toBe(50);
  });
});
