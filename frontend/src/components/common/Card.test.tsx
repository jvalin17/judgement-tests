import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { Card, CardBack } from "./Card";
import { SettingsProvider } from "../../context/SettingsContext";
import { makeCard } from "../../test/helpers";

function renderCard(overrides: Partial<{
  card: { suit: string; rank: number | string };
  playable: boolean;
  selected: boolean;
  dimmed: boolean;
  small: boolean;
  onClick: () => void;
}> = {}) {
  const props = {
    card: makeCard("spades", "14"),
    playable: false,
    ...overrides,
  };
  return render(
    <SettingsProvider>
      <Card {...props} />
    </SettingsProvider>
  );
}

describe("Card", () => {
  it("renders rank display for Ace", () => {
    renderCard({ card: makeCard("spades", "14") });
    // Ace displays as "A" — appears in top and bottom corners
    const rankElements = screen.getAllByText("A");
    expect(rankElements.length).toBeGreaterThanOrEqual(2);
  });

  it("renders rank display for Ten", () => {
    renderCard({ card: makeCard("hearts", "10") });
    const rankElements = screen.getAllByText("10");
    expect(rankElements.length).toBeGreaterThanOrEqual(2);
  });

  it("renders rank display for King", () => {
    renderCard({ card: makeCard("diamonds", "13") });
    const rankElements = screen.getAllByText("K");
    expect(rankElements.length).toBeGreaterThanOrEqual(2);
  });

  it("applies playable class when playable=true", () => {
    const { container } = renderCard({ playable: true });
    const cardDiv = container.querySelector(".card");
    expect(cardDiv).not.toBeNull();
    expect(cardDiv!.className).toContain("playable");
  });

  it("does not apply playable class when playable=false", () => {
    const { container } = renderCard({ playable: false });
    const cardDiv = container.querySelector(".card");
    expect(cardDiv).not.toBeNull();
    expect(cardDiv!.className).not.toContain("playable");
  });

  it("has role=button when playable", () => {
    renderCard({ playable: true });
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("does not have role=button when not playable", () => {
    renderCard({ playable: false });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("calls onClick when playable and clicked", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    renderCard({ playable: true, onClick: handleClick });
    await user.click(screen.getByRole("button"));
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it("does not call onClick when not playable and clicked", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    const { container } = renderCard({ playable: false, onClick: handleClick });
    const cardDiv = container.querySelector(".card")!;
    await user.click(cardDiv);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it("applies dimmed class", () => {
    const { container } = renderCard({ dimmed: true });
    const cardDiv = container.querySelector(".card");
    expect(cardDiv!.className).toContain("dimmed");
  });

  it("applies small class", () => {
    const { container } = renderCard({ small: true });
    const cardDiv = container.querySelector(".card");
    expect(cardDiv!.className).toContain("small");
  });
});

describe("CardBack", () => {
  it("renders without error", () => {
    const { container } = render(
      <SettingsProvider>
        <CardBack />
      </SettingsProvider>
    );
    expect(container.querySelector(".cardBack")).toBeInTheDocument();
  });

  it("applies small class when small=true", () => {
    const { container } = render(
      <SettingsProvider>
        <CardBack small />
      </SettingsProvider>
    );
    const cardBack = container.querySelector(".cardBack");
    expect(cardBack).not.toBeNull();
    expect(cardBack!.className).toContain("small");
  });
});
