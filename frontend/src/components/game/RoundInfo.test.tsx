import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RoundInfo } from "./RoundInfo";

const defaultProps = () => ({
  roundNumber: 3,
  totalRounds: 10,
  numCards: 5,
  trumpSuit: "spades",
  playerCount: 4,
  mustLoseMode: false,
  challengeMode: false,
});

describe("RoundInfo", () => {
  it("returns null when roundNumber is null", () => {
    const { container } = render(
      <RoundInfo
        roundNumber={null}
        totalRounds={10}
        numCards={5}
        trumpSuit="spades"
        playerCount={4}
        mustLoseMode={false}
        challengeMode={false}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows Round X text", () => {
    render(<RoundInfo {...defaultProps()} />);
    expect(screen.getByText("Round 3")).toBeInTheDocument();
  });

  it("shows X cards text", () => {
    render(<RoundInfo {...defaultProps()} />);
    expect(screen.getByText("5 cards")).toBeInTheDocument();
  });

  it("hover tooltip shows 'Round X of Y' when totalRounds provided", () => {
    render(<RoundInfo {...defaultProps()} />);
    const roundText = screen.getByText("Round 3");
    expect(roundText).toHaveAttribute("title", "Round 3 of 10");
  });

  it("hover tooltip shows 'Round X' when totalRounds is null", () => {
    render(<RoundInfo {...defaultProps()} totalRounds={null} />);
    const roundText = screen.getByText("Round 3");
    expect(roundText).toHaveAttribute("title", "Round 3");
  });

  it("shows turbulence icon when mustLoseMode is true", () => {
    render(<RoundInfo {...defaultProps()} mustLoseMode={true} />);
    expect(screen.getByTitle("Turbulence — someone must lose every round")).toBeInTheDocument();
  });

  it("does not show turbulence icon when mustLoseMode is false", () => {
    render(<RoundInfo {...defaultProps()} mustLoseMode={false} />);
    expect(screen.queryByTitle("Turbulence — someone must lose every round")).not.toBeInTheDocument();
  });

  it("shows challenge icon when challengeMode is true", () => {
    render(<RoundInfo {...defaultProps()} challengeMode={true} />);
    expect(screen.getByTitle("Challenge — AI plays at full strength")).toBeInTheDocument();
  });

  it("shows casual icon when challengeMode is false", () => {
    render(<RoundInfo {...defaultProps()} challengeMode={false} />);
    expect(screen.getByTitle("Casual — AI adapts to your level")).toBeInTheDocument();
  });

  it("does not show challenge icon when in casual mode", () => {
    render(<RoundInfo {...defaultProps()} challengeMode={false} />);
    expect(screen.queryByTitle("Challenge — AI plays at full strength")).not.toBeInTheDocument();
  });

  it("positions roundIslandTop for 3 players", () => {
    const { container } = render(<RoundInfo {...defaultProps()} playerCount={3} />);
    const island = container.firstChild as HTMLElement;
    expect(island.className).toContain("roundIslandTop");
    expect(island.className).not.toContain("roundIslandBottom");
  });

  it("positions roundIslandTop for 5 players", () => {
    const { container } = render(<RoundInfo {...defaultProps()} playerCount={5} />);
    const island = container.firstChild as HTMLElement;
    expect(island.className).toContain("roundIslandTop");
  });

  it("positions roundIslandBottom for 4 players", () => {
    const { container } = render(<RoundInfo {...defaultProps()} playerCount={4} />);
    const island = container.firstChild as HTMLElement;
    expect(island.className).toContain("roundIslandBottom");
  });

  it("positions roundIslandBottom for 6 players", () => {
    const { container } = render(<RoundInfo {...defaultProps()} playerCount={6} />);
    const island = container.firstChild as HTMLElement;
    expect(island.className).toContain("roundIslandBottom");
  });
});
