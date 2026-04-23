import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BidSelector } from "./BidSelector";
import { makePlayer, makeCard } from "../../test/helpers";

const defaultProps = () => ({
  validBids: [0, 1, 2, 3],
  numCards: 5,
  onBid: vi.fn(),
  bids: [],
  players: [
    makePlayer({ id: "p1", name: "Alice" }),
    makePlayer({ id: "p2", name: "Bob" }),
    makePlayer({ id: "p3", name: "Charlie" }),
  ],
  playerId: "p1",
  trumpSuit: "spades",
  cumulativeScores: { p1: 21, p2: 10, p3: -5 },
});

describe("BidSelector", () => {
  it("renders bid buttons 0 through numCards", () => {
    render(<BidSelector {...defaultProps()} />);
    for (let i = 0; i <= 5; i++) {
      expect(screen.getByRole("button", { name: String(i) })).toBeInTheDocument();
    }
  });

  it("disables invalid bid buttons", () => {
    render(<BidSelector {...defaultProps()} validBids={[0, 2]} />);
    expect(screen.getByRole("button", { name: "0" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "1" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "2" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "3" })).toBeDisabled();
  });

  it("calls onBid when a valid bid button is clicked", async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<BidSelector {...props} />);
    await user.click(screen.getByRole("button", { name: "2" }));
    expect(props.onBid).toHaveBeenCalledWith(2);
  });

  it("does not call onBid when a disabled button is clicked", async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    props.validBids = [0, 2];
    render(<BidSelector {...props} />);
    await user.click(screen.getByRole("button", { name: "1" }));
    expect(props.onBid).not.toHaveBeenCalled();
  });

  it("shows the player score", () => {
    render(<BidSelector {...defaultProps()} />);
    expect(screen.getByText("Score: 21")).toBeInTheDocument();
  });

  it("shows total bids so far", () => {
    const props = defaultProps();
    props.bids = [{ player_id: "p2", amount: 3 }];
    render(<BidSelector {...props} />);
    expect(screen.getByText("3/5")).toBeInTheDocument();
  });

  it("shows trump suit symbol", () => {
    render(<BidSelector {...defaultProps()} />);
    expect(screen.getByText("♠")).toBeInTheDocument();
  });

  it("shows 'You' for current player in bid table", () => {
    render(<BidSelector {...defaultProps()} />);
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("Charlie")).toBeInTheDocument();
  });

  it("shows placed bid amounts in the bid table", () => {
    const props = defaultProps();
    props.bids = [
      { player_id: "p2", amount: 2 },
      { player_id: "p3", amount: 0 },
    ];
    render(<BidSelector {...props} />);
    // Bob bid 2, Charlie bid 0, player sees "?"
    expect(screen.getByText("?")).toBeInTheDocument();
  });

  it("renders with zero score", () => {
    const props = defaultProps();
    props.cumulativeScores = {};
    render(<BidSelector {...props} />);
    expect(screen.getByText("Score: 0")).toBeInTheDocument();
  });
});
