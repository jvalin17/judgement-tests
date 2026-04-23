import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Modal } from "./Modal";

describe("Modal", () => {
  it("renders the title text", () => {
    render(<Modal title="Test Title">Content</Modal>);
    expect(screen.getByText("Test Title")).toBeInTheDocument();
  });

  it("renders children content", () => {
    render(<Modal title="Title"><p>Hello world</p></Modal>);
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("shows close button when onClose is provided", () => {
    const handleClose = vi.fn();
    render(<Modal title="Title" onClose={handleClose}>Content</Modal>);
    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
  });

  it("close button calls onClose", () => {
    const handleClose = vi.fn();
    render(<Modal title="Title" onClose={handleClose}>Content</Modal>);
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("does not render close button when onClose is not provided", () => {
    render(<Modal title="Title">Content</Modal>);
    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument();
  });

  it("ESC key calls onClose", () => {
    const handleClose = vi.fn();
    render(<Modal title="Title" onClose={handleClose}>Content</Modal>);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("ESC key does nothing when onClose is not provided", () => {
    // Should not throw
    render(<Modal title="Title">Content</Modal>);
    fireEvent.keyDown(document, { key: "Escape" });
  });

  it("clicking overlay calls onClose", () => {
    const handleClose = vi.fn();
    render(<Modal title="Title" onClose={handleClose}>Content</Modal>);
    // The overlay is the outermost div with modalOverlay class
    const overlay = screen.getByText("Title").closest(`.modalOverlay`)!;
    fireEvent.click(overlay);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("clicking modal content does NOT call onClose (stopPropagation)", () => {
    const handleClose = vi.fn();
    render(<Modal title="Title" onClose={handleClose}>Content</Modal>);
    // Click on the modal body content, not the overlay
    const modalBody = screen.getByText("Content");
    fireEvent.click(modalBody);
    expect(handleClose).not.toHaveBeenCalled();
  });
});
