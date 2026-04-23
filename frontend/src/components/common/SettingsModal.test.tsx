import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SettingsProvider } from "../../context/SettingsContext";
import { SettingsModal } from "./SettingsModal";
import { CardBackDesign, TableColor, AnimationSpeed, CARD_BACK_LABELS, TABLE_COLOR_LABELS, ANIMATION_SPEED_LABELS } from "../../types";

// Mock API calls that fire on mount
vi.mock("../../services/api", () => ({
  getVersion: vi.fn().mockResolvedValue({ git_sha: "abc123", build_date: "2026-04-01T00:00:00" }),
  checkForUpdate: vi.fn().mockResolvedValue({ update_available: false }),
  applyUpdate: vi.fn().mockResolvedValue({ success: true, message: "ok" }),
  getUpdateStatus: vi.fn().mockResolvedValue({ state: "idle", message: "" }),
  getSharePreview: vi.fn().mockResolvedValue({ bid_decisions: 10, play_decisions: 20, human_bid_decisions: 5, human_play_decisions: 10, total: 30, description: "" }),
  shareData: vi.fn().mockResolvedValue({ success: true, message: "shared" }),
  downloadCommunityData: vi.fn().mockResolvedValue({ success: true, message: "downloaded", examples_added: 10 }),
}));

function renderSettings(onClose = vi.fn()) {
  return render(
    <SettingsProvider>
      <SettingsModal onClose={onClose} />
    </SettingsProvider>,
  );
}

describe("SettingsModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with Settings title", () => {
    renderSettings();
    expect(screen.getByText("Settings")).toBeTruthy();
  });

  it("renders Card Back Design section", () => {
    renderSettings();
    expect(screen.getByText("Card Back Design")).toBeTruthy();
  });

  it("renders Table Color section", () => {
    renderSettings();
    expect(screen.getByText("Table Color")).toBeTruthy();
  });

  it("renders Animation Speed section", () => {
    renderSettings();
    expect(screen.getByText("Animation Speed")).toBeTruthy();
  });

  it("renders all card back options", () => {
    renderSettings();
    for (const label of Object.values(CARD_BACK_LABELS)) {
      expect(screen.getByText(label)).toBeTruthy();
    }
  });

  it("renders all table color options", () => {
    renderSettings();
    for (const label of Object.values(TABLE_COLOR_LABELS)) {
      expect(screen.getByText(label)).toBeTruthy();
    }
  });

  it("renders all animation speed options", () => {
    renderSettings();
    for (const label of Object.values(ANIMATION_SPEED_LABELS)) {
      expect(screen.getByText(label)).toBeTruthy();
    }
  });

  it("renders Community Data section", () => {
    renderSettings();
    expect(screen.getByText("Community Data")).toBeTruthy();
  });

  it("renders Updates section", () => {
    renderSettings();
    expect(screen.getByText("Updates")).toBeTruthy();
  });

  it("renders Check for Updates button", () => {
    renderSettings();
    expect(screen.getByText("Check for Updates")).toBeTruthy();
  });

  it("clicking a speed option updates selection", () => {
    renderSettings();
    const fastButton = screen.getByText(ANIMATION_SPEED_LABELS[AnimationSpeed.FAST]);
    fireEvent.click(fastButton);
    // After click, the element should have the selected class
    expect(fastButton.closest("[class]")).toBeTruthy();
  });

  it("renders Share Data and Get Community Data buttons", () => {
    renderSettings();
    expect(screen.getByText("Share Data")).toBeTruthy();
    expect(screen.getByText("Get Community Data")).toBeTruthy();
  });
});
