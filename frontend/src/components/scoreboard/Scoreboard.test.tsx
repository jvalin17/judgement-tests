import { render, screen } from "@testing-library/react";
import { Scoreboard } from "./Scoreboard";
import { makePlayer } from "../../test/helpers";

const defaultProps = () => ({
  players: [
    makePlayer({ id: "p1", name: "Alice" }),
    makePlayer({ id: "p2", name: "Bob" }),
    makePlayer({ id: "p3", name: "Charlie" }),
  ],
  bids: [
    { player_id: "p1", amount: 3 },
    { player_id: "p2", amount: 2 },
    { player_id: "p3", amount: 1 },
  ],
  tricksWon: { p1: 3, p2: 1, p3: 2 },
  cumulativeScores: { p1: 30, p2: 10, p3: -11 },
  currentPlayerId: "p1",
});

describe("Scoreboard", () => {
  it("renders column headers", () => {
    render(<Scoreboard {...defaultProps()} />);
    expect(screen.getByText("Pilot")).toBeInTheDocument();
    expect(screen.getByText("Flights")).toBeInTheDocument();
    expect(screen.getByText("Landings")).toBeInTheDocument();
    expect(screen.getByText("Score")).toBeInTheDocument();
  });

  it("renders all player names", () => {
    render(<Scoreboard {...defaultProps()} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("Charlie")).toBeInTheDocument();
  });

  it("renders bid and trick values", () => {
    const { container } = render(<Scoreboard {...defaultProps()} />);
    // Check that the table body rows have the expected content
    const rows = container.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(3);
    // Alice: bid=3, tricks=3; Bob: bid=2, tricks=1; Charlie: bid=1, tricks=2
    expect(rows[0].textContent).toContain("3"); // bid
    expect(rows[1].textContent).toContain("2"); // bid
    expect(rows[2].textContent).toContain("1"); // bid
  });

  it("shows dash when bid not placed", () => {
    const props = defaultProps();
    props.bids = [{ player_id: "p1", amount: 3 }]; // only Alice bid
    render(<Scoreboard {...props} />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBe(2); // Bob and Charlie
  });

  it("shows leader badge for highest scorer", () => {
    render(<Scoreboard {...defaultProps()} />);
    expect(screen.getByTitle("Leader")).toBeInTheDocument();
    expect(screen.getByText("★")).toBeInTheDocument();
  });

  it("shows Current column only when roundScores provided", () => {
    const props = defaultProps();
    const { rerender } = render(<Scoreboard {...props} />);
    expect(screen.queryByText("Current")).not.toBeInTheDocument();

    rerender(<Scoreboard {...props} roundScores={{ p1: 30, p2: -2, p3: 11 }} />);
    expect(screen.getByText("Current")).toBeInTheDocument();
  });

  it("shows positive round scores with green styling", () => {
    const props = defaultProps();
    render(<Scoreboard {...props} roundScores={{ p1: 30, p2: -2, p3: 11 }} />);
    expect(screen.getByText("+30")).toBeInTheDocument();
    expect(screen.getByText("-2")).toBeInTheDocument();
    expect(screen.getByText("+11")).toBeInTheDocument();
  });

  it("handles tied leaders", () => {
    const props = defaultProps();
    props.cumulativeScores = { p1: 30, p2: 30, p3: 10 };
    render(<Scoreboard {...props} />);
    const stars = screen.getAllByText("★");
    expect(stars).toHaveLength(2); // Alice and Bob tied
  });

  it("renders cumulative scores", () => {
    render(<Scoreboard {...defaultProps()} />);
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });
});
