import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SuitIcon } from "./SuitIcon";
import { Suit, SUIT_SYMBOLS } from "../../types";

describe("SuitIcon", () => {
  it("renders correct symbol for spades", () => {
    render(<SuitIcon suit={Suit.SPADES} />);
    expect(screen.getByText(SUIT_SYMBOLS[Suit.SPADES])).toBeInTheDocument();
  });

  it("renders correct symbol for diamonds", () => {
    render(<SuitIcon suit={Suit.DIAMONDS} />);
    expect(screen.getByText(SUIT_SYMBOLS[Suit.DIAMONDS])).toBeInTheDocument();
  });

  it("renders correct symbol for clubs", () => {
    render(<SuitIcon suit={Suit.CLUBS} />);
    expect(screen.getByText(SUIT_SYMBOLS[Suit.CLUBS])).toBeInTheDocument();
  });

  it("renders correct symbol for hearts", () => {
    render(<SuitIcon suit={Suit.HEARTS} />);
    expect(screen.getByText(SUIT_SYMBOLS[Suit.HEARTS])).toBeInTheDocument();
  });

  it("applies black color for spades", () => {
    render(<SuitIcon suit={Suit.SPADES} />);
    const element = screen.getByLabelText("spades");
    expect(element.style.color).toBe("black");
  });

  it("applies black color for clubs", () => {
    render(<SuitIcon suit={Suit.CLUBS} />);
    const element = screen.getByLabelText("clubs");
    expect(element.style.color).toBe("black");
  });

  it("applies red color for hearts", () => {
    render(<SuitIcon suit={Suit.HEARTS} />);
    const element = screen.getByLabelText("hearts");
    expect(element.style.color).toBe("red");
  });

  it("applies red color for diamonds", () => {
    render(<SuitIcon suit={Suit.DIAMONDS} />);
    const element = screen.getByLabelText("diamonds");
    expect(element.style.color).toBe("red");
  });

  it("uses 1rem font-size for sm size", () => {
    render(<SuitIcon suit={Suit.SPADES} size="sm" />);
    const element = screen.getByLabelText("spades");
    expect(element.style.fontSize).toBe("1rem");
  });

  it("uses 1.5rem font-size for md size (default)", () => {
    render(<SuitIcon suit={Suit.SPADES} />);
    const element = screen.getByLabelText("spades");
    expect(element.style.fontSize).toBe("1.5rem");
  });

  it("uses 2rem font-size for lg size", () => {
    render(<SuitIcon suit={Suit.SPADES} size="lg" />);
    const element = screen.getByLabelText("spades");
    expect(element.style.fontSize).toBe("2rem");
  });

  it("sets aria-label to the suit name", () => {
    render(<SuitIcon suit={Suit.HEARTS} />);
    expect(screen.getByLabelText("hearts")).toBeInTheDocument();
  });
});
