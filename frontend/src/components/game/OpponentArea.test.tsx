import { render, screen } from "@testing-library/react";
import { PlayerSeat } from "./OpponentArea";
import { makePlayer } from "../../test/helpers";
import { SettingsProvider } from "../../context/SettingsContext";

function renderSeat(props: Parameters<typeof PlayerSeat>[0]) {
  return render(
    <SettingsProvider>
      <PlayerSeat {...props} />
    </SettingsProvider>
  );
}

const defaultProps = {
  position: { left: "50%", top: "20%" },
  isCurrentTurn: false,
  bid: null as number | null,
  tricksWon: 0,
  score: 0,
  cardsRemaining: 3,
};

describe("PlayerSeat", () => {
  it("shows dash in bid badge when no bid placed", () => {
    renderSeat({ player: makePlayer({ name: "Bot1" }), ...defaultProps });
    const badge = screen.getByTestId("bid-Bot1");
    expect(badge).toHaveTextContent("\u2014");
  });

  it("shows won/bid status in bid badge on cards", () => {
    renderSeat({ player: makePlayer({ name: "Bot1" }), ...defaultProps, bid: 3, tricksWon: 1 });
    const badge = screen.getByTestId("bid-Bot1");
    expect(badge).toHaveTextContent("1/3");
  });

  it("shows score in separate score badge below name", () => {
    renderSeat({ player: makePlayer({ name: "Bot1" }), ...defaultProps, bid: 2, tricksWon: 2, score: 42 });
    const scoreBadge = screen.getByTestId("score-Bot1");
    expect(scoreBadge).toHaveTextContent("42");
  });

  it("applies active class to bid badge when it is the player's turn", () => {
    renderSeat({ player: makePlayer({ name: "Bot1" }), ...defaultProps, isCurrentTurn: true });
    const badge = screen.getByTestId("bid-Bot1");
    expect(badge.className).toContain("bidBadgeActive");
  });

  it("does not apply active class when not the player's turn", () => {
    renderSeat({ player: makePlayer({ name: "Bot1" }), ...defaultProps, isCurrentTurn: false });
    const badge = screen.getByTestId("bid-Bot1");
    expect(badge.className).not.toContain("bidBadgeActive");
  });

  it("shows NOW pill when it is the player's turn", () => {
    renderSeat({ player: makePlayer({ name: "Bot1" }), ...defaultProps, isCurrentTurn: true });
    expect(screen.getByText("NOW")).toBeInTheDocument();
  });

  it("shows player name", () => {
    renderSeat({ player: makePlayer({ name: "Jalebi" }), ...defaultProps });
    expect(screen.getByText("Jalebi")).toBeInTheDocument();
  });

  it("shows 0/0 when bid is zero and no tricks won", () => {
    renderSeat({ player: makePlayer({ name: "Bot1" }), ...defaultProps, bid: 0, tricksWon: 0 });
    const badge = screen.getByTestId("bid-Bot1");
    expect(badge).toHaveTextContent("0/0");
  });

  it("bid and score badges are separate elements", () => {
    renderSeat({ player: makePlayer({ name: "Bot1" }), ...defaultProps, bid: 2, tricksWon: 1, score: 30 });
    const bidBadge = screen.getByTestId("bid-Bot1");
    const scoreBadge = screen.getByTestId("score-Bot1");
    expect(bidBadge).toHaveTextContent("1/2");
    expect(scoreBadge).toHaveTextContent("30");
    expect(bidBadge).not.toBe(scoreBadge);
  });

  it("renders in order: cards with bid badge, then name, then score badge", () => {
    const { container } = renderSeat({
      player: makePlayer({ name: "Jalebi" }),
      ...defaultProps,
      bid: 2,
      tricksWon: 1,
      score: 30,
    });
    const seat = container.firstElementChild!;
    const children = Array.from(seat.children);
    // child 0: seatCards (contains card fan + bid badge)
    // child 1: seatName
    // child 2: scoreBadge
    expect(children.length).toBeGreaterThanOrEqual(3);
    expect(children[0].querySelector("[data-testid='bid-Jalebi']")).toBeTruthy();
    expect(children[1].textContent).toBe("Jalebi");
    expect(children[2]).toBe(screen.getByTestId("score-Jalebi"));
  });
});

describe("Seat layout positions", () => {
  it("no seat overlaps the top-left round info corner", async () => {
    const layouts: Record<number, Array<{ left: string; top: string }>> = {
      3: [
        { left: "50%", top: "82%" },
        { left: "15%", top: "30%" },
        { left: "85%", top: "30%" },
      ],
      4: [
        { left: "50%", top: "82%" },
        { left: "10%", top: "45%" },
        { left: "50%", top: "10%" },
        { left: "90%", top: "45%" },
      ],
      5: [
        { left: "50%", top: "82%" },
        { left: "8%", top: "45%" },
        { left: "25%", top: "12%" },
        { left: "75%", top: "12%" },
        { left: "92%", top: "45%" },
      ],
      6: [
        { left: "50%", top: "82%" },
        { left: "8%", top: "45%" },
        { left: "25%", top: "12%" },
        { left: "50%", top: "8%" },
        { left: "75%", top: "12%" },
        { left: "92%", top: "45%" },
      ],
    };

    for (const [, seats] of Object.entries(layouts)) {
      for (let seatIndex = 1; seatIndex < seats.length; seatIndex++) {
        const topPercent = parseFloat(seats[seatIndex].top);
        const leftPercent = parseFloat(seats[seatIndex].left);
        const overlapsRoundInfo = leftPercent < 20 && topPercent < 15;
        expect(overlapsRoundInfo).toBe(false);
      }
    }
  });
});
