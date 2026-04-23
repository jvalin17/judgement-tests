import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";

describe("Button", () => {
  it("renders children text", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument();
  });

  it("applies primary class by default", () => {
    render(<Button>Primary</Button>);
    const button = screen.getByRole("button");
    expect(button.className).toContain("primary");
  });

  it("applies secondary variant class", () => {
    render(<Button variant="secondary">Secondary</Button>);
    const button = screen.getByRole("button");
    expect(button.className).toContain("secondary");
  });

  it("applies danger variant class", () => {
    render(<Button variant="danger">Danger</Button>);
    const button = screen.getByRole("button");
    expect(button.className).toContain("danger");
  });

  it("applies fullWidth class when fullWidth is true", () => {
    render(<Button fullWidth>Wide</Button>);
    const button = screen.getByRole("button");
    expect(button.className).toContain("fullWidth");
  });

  it("does not apply fullWidth class by default", () => {
    render(<Button>Normal</Button>);
    const button = screen.getByRole("button");
    expect(button.className).not.toContain("fullWidth");
  });

  it("applies small size class", () => {
    render(<Button size="small">Small</Button>);
    const button = screen.getByRole("button");
    expect(button.className).toContain("small");
  });

  it("applies large size class", () => {
    render(<Button size="large">Large</Button>);
    const button = screen.getByRole("button");
    expect(button.className).toContain("large");
  });

  it("does not apply size class for medium (default)", () => {
    render(<Button>Medium</Button>);
    const button = screen.getByRole("button");
    expect(button.className).not.toContain("small");
    expect(button.className).not.toContain("large");
  });

  it("fires onClick when clicked", async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={handleClick}>Click</Button>);
    await user.click(screen.getByRole("button"));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("does not fire onClick when disabled", async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={handleClick} disabled>Disabled</Button>);
    await user.click(screen.getByRole("button"));
    expect(handleClick).not.toHaveBeenCalled();
  });

  it("passes through extra HTML attributes", () => {
    render(<Button type="submit">Submit</Button>);
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("type", "submit");
  });

  it("merges custom className with generated classes", () => {
    render(<Button className="custom-class">Custom</Button>);
    const button = screen.getByRole("button");
    expect(button.className).toContain("custom-class");
    expect(button.className).toContain("button");
  });
});
