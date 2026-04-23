import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FinalResults } from "./FinalResults";
import { makePlayer } from "../../test/helpers";

// Mock the API calls used by SharePrompt
vi.mock("../../services/api", () => ({
  getSharePreview: vi.fn().mockResolvedValue({ bid_decisions: 0, play_decisions: 0, human_bid_decisions: 0, human_play_decisions: 0, total: 0 }),
  shareData: vi.fn(),
  getShareStatus: vi.fn(),
}));

const defaultProps = () => ({
  players: [
    makePlayer({ id: "p1", name: "Alice" }),
    makePlayer({ id: "p2", name: "Bob" }),
    makePlayer({ id: "p3", name: "Charlie" }),
  ],
  finalScores: { p1: 50, p2: 30, p3: -10 },
  awardedPersona: null,
  playerId: "p1",
  onPlayAgain: vi.fn(),
});

describe("FinalResults", () => {
  it("renders Game Over title", () => {
    render(<FinalResults {...defaultProps()} />);
    expect(screen.getByText("Game Over")).toBeInTheDocument();
  });

  it("shows the winner name", () => {
    render(<FinalResults {...defaultProps()} />);
    expect(screen.getByText("Winner")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("shows 'Winners' for ties", () => {
    const props = defaultProps();
    props.finalScores = { p1: 50, p2: 50, p3: 10 };
    render(<FinalResults {...props} />);
    expect(screen.getByText("Winners")).toBeInTheDocument();
    expect(screen.getByText("Alice & Bob")).toBeInTheDocument();
  });

  it("ranks players by score descending", () => {
    const { container } = render(<FinalResults {...defaultProps()} />);
    const scoreRows = container.querySelectorAll(".finalScoreRow");
    expect(scoreRows).toHaveLength(3);
    // First row should be highest scorer
    expect(scoreRows[0].textContent).toContain("50");
    expect(scoreRows[2].textContent).toContain("-10");
  });

  it("shows 'Your score' for the current player", () => {
    render(<FinalResults {...defaultProps()} />);
    expect(screen.getByText("Your score")).toBeInTheDocument();
  });

  it("calls onPlayAgain when Play Again is clicked", async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<FinalResults {...props} />);
    await user.click(screen.getByText("Play Again"));
    expect(props.onPlayAgain).toHaveBeenCalledOnce();
  });

  it("renders persona card when awarded", () => {
    const props = defaultProps();
    props.awardedPersona = {
      persona_name: "Iron Man",
      persona_category: "superhero",
      persona_tagline: "Genius, billionaire, philanthropist",
      similarity: 0.95,
      traits: { risk: 0.8, planning: 0.9, patience: 0.3 },
      player_traits: { risk: 0.7, planning: 0.85, patience: 0.4 },
    };
    render(<FinalResults {...props} />);
    expect(screen.getAllByText("Iron Man").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Your Play Style")).toBeInTheDocument();
    expect(screen.getByText("Superhero")).toBeInTheDocument();
    expect(screen.getByText("Genius, billionaire, philanthropist")).toBeInTheDocument();
  });

  it("does not render persona card when not awarded", () => {
    render(<FinalResults {...defaultProps()} />);
    expect(screen.queryByText("Your Play Style")).not.toBeInTheDocument();
  });

  it("renders celebration effects based on player rank", () => {
    const { container } = render(<FinalResults {...defaultProps()} />);
    // 1st place player should get confetti containers
    const ariaHidden = container.querySelectorAll("[aria-hidden='true']");
    expect(ariaHidden.length).toBeGreaterThan(0);
  });
});
