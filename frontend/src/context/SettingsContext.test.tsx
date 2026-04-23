import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { SettingsProvider, useSettings } from "./SettingsContext";
import { DEFAULT_SETTINGS } from "../types";

function wrapper({ children }: { children: ReactNode }) {
  return <SettingsProvider>{children}</SettingsProvider>;
}

describe("SettingsContext", () => {
  it("provides default settings", () => {
    const { result } = renderHook(() => useSettings(), { wrapper });
    expect(result.current.settings).toEqual(DEFAULT_SETTINGS);
  });

  it("throws when used outside provider", () => {
    expect(() => {
      renderHook(() => useSettings());
    }).toThrow("useSettings must be used within a SettingsProvider");
  });

  it("updateCardBack changes card back design", () => {
    const { result } = renderHook(() => useSettings(), { wrapper });

    act(() => {
      result.current.updateCardBack("cockpit_navy" as any);
    });

    expect(result.current.settings.cardBack).toBe("cockpit_navy");
  });

  it("updateTableColor changes table color", () => {
    const { result } = renderHook(() => useSettings(), { wrapper });

    act(() => {
      result.current.updateTableColor("navy_blue" as any);
    });

    expect(result.current.settings.tableColor).toBe("navy_blue");
  });

  it("updateAnimationSpeed changes animation speed", () => {
    const { result } = renderHook(() => useSettings(), { wrapper });

    act(() => {
      result.current.updateAnimationSpeed("fast" as any);
    });

    expect(result.current.settings.animationSpeed).toBe("fast");
  });

  it("applies CSS variables for table color on change", () => {
    const { result } = renderHook(() => useSettings(), { wrapper });

    act(() => {
      result.current.updateTableColor("navy_blue" as any);
    });

    const root = document.documentElement.style;
    expect(root.getPropertyValue("--color-table")).toBeTruthy();
    expect(root.getPropertyValue("--color-table-dark")).toBeTruthy();
    expect(root.getPropertyValue("--color-table-light")).toBeTruthy();
  });

  it("applies CSS variables for animation speed on change", () => {
    const { result } = renderHook(() => useSettings(), { wrapper });

    act(() => {
      result.current.updateAnimationSpeed("fast" as any);
    });

    const root = document.documentElement.style;
    expect(root.getPropertyValue("--transition-fast")).toContain("ms");
    expect(root.getPropertyValue("--transition-base")).toContain("ms");
    expect(root.getPropertyValue("--transition-slow")).toContain("ms");
  });

  it("preserves other settings when updating one", () => {
    const { result } = renderHook(() => useSettings(), { wrapper });

    act(() => {
      result.current.updateCardBack("cockpit_navy" as any);
    });
    act(() => {
      result.current.updateTableColor("navy_blue" as any);
    });

    expect(result.current.settings.cardBack).toBe("cockpit_navy");
    expect(result.current.settings.tableColor).toBe("navy_blue");
    expect(result.current.settings.animationSpeed).toBe(DEFAULT_SETTINGS.animationSpeed);
  });
});
