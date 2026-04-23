import { describe, it, expect } from "vitest";
import {
  CardBackDesign,
  TableColor,
  AnimationSpeed,
  DEFAULT_SETTINGS,
  TABLE_COLOR_MAP,
  TABLE_COLOR_LABELS,
  CARD_BACK_LABELS,
  ANIMATION_SPEED_MAP,
  ANIMATION_SPEED_LABELS,
} from "./settings";

describe("DEFAULT_SETTINGS", () => {
  it("has classic blue card back", () => {
    expect(DEFAULT_SETTINGS.cardBack).toBe(CardBackDesign.CLASSIC_BLUE);
  });

  it("has classic green table color", () => {
    expect(DEFAULT_SETTINGS.tableColor).toBe(TableColor.CLASSIC_GREEN);
  });

  it("has slow animation speed", () => {
    expect(DEFAULT_SETTINGS.animationSpeed).toBe(AnimationSpeed.SLOW);
  });
});

describe("TABLE_COLOR_MAP", () => {
  const allColors = Object.values(TableColor);

  it("has entries for all 10 table colors", () => {
    expect(Object.keys(TABLE_COLOR_MAP)).toHaveLength(10);
  });

  it("every color has base, dark, and light properties", () => {
    for (const color of allColors) {
      const entry = TABLE_COLOR_MAP[color];
      expect(entry).toHaveProperty("base");
      expect(entry).toHaveProperty("dark");
      expect(entry).toHaveProperty("light");
    }
  });

  it("all values are valid hex colors", () => {
    const hexPattern = /^#[0-9a-f]{6}$/;
    for (const color of allColors) {
      const entry = TABLE_COLOR_MAP[color];
      expect(entry.base).toMatch(hexPattern);
      expect(entry.dark).toMatch(hexPattern);
      expect(entry.light).toMatch(hexPattern);
    }
  });
});

describe("ANIMATION_SPEED_MAP", () => {
  const allSpeeds = Object.values(AnimationSpeed);

  it("has entries for all 3 speeds", () => {
    expect(Object.keys(ANIMATION_SPEED_MAP)).toHaveLength(3);
  });

  it("every speed has fast, base, and slow properties", () => {
    for (const speed of allSpeeds) {
      const entry = ANIMATION_SPEED_MAP[speed];
      expect(entry).toHaveProperty("fast");
      expect(entry).toHaveProperty("base");
      expect(entry).toHaveProperty("slow");
    }
  });

  it("fast < base < slow for each speed setting", () => {
    for (const speed of allSpeeds) {
      const entry = ANIMATION_SPEED_MAP[speed];
      expect(entry.fast).toBeLessThan(entry.base);
      expect(entry.base).toBeLessThan(entry.slow);
    }
  });

  it("fast setting has lower durations than medium, which is lower than slow", () => {
    expect(ANIMATION_SPEED_MAP[AnimationSpeed.FAST].base).toBeLessThan(
      ANIMATION_SPEED_MAP[AnimationSpeed.MEDIUM].base,
    );
    expect(ANIMATION_SPEED_MAP[AnimationSpeed.MEDIUM].base).toBeLessThan(
      ANIMATION_SPEED_MAP[AnimationSpeed.SLOW].base,
    );
  });
});

describe("TABLE_COLOR_LABELS", () => {
  it("has labels for all 10 colors", () => {
    expect(Object.keys(TABLE_COLOR_LABELS)).toHaveLength(10);
  });

  it("all labels are non-empty strings", () => {
    for (const label of Object.values(TABLE_COLOR_LABELS)) {
      expect(typeof label).toBe("string");
      expect(label.length).toBeGreaterThan(0);
    }
  });

  it("maps specific colors correctly", () => {
    expect(TABLE_COLOR_LABELS[TableColor.CLASSIC_GREEN]).toBe("Classic Green");
    expect(TABLE_COLOR_LABELS[TableColor.MIDNIGHT_BLACK]).toBe("Midnight");
    expect(TABLE_COLOR_LABELS[TableColor.ROYAL_PURPLE]).toBe("Royal Purple");
  });
});

describe("CARD_BACK_LABELS", () => {
  it("has labels for all 9 designs", () => {
    expect(Object.keys(CARD_BACK_LABELS)).toHaveLength(9);
  });

  it("all labels are non-empty strings", () => {
    for (const label of Object.values(CARD_BACK_LABELS)) {
      expect(typeof label).toBe("string");
      expect(label.length).toBeGreaterThan(0);
    }
  });

  it("maps specific designs correctly", () => {
    expect(CARD_BACK_LABELS[CardBackDesign.CLASSIC_BLUE]).toBe("Classic Blue");
    expect(CARD_BACK_LABELS[CardBackDesign.BLACKBOX]).toBe("Black Box");
    expect(CARD_BACK_LABELS[CardBackDesign.RED_EYE]).toBe("Red Eye");
  });
});

describe("ANIMATION_SPEED_LABELS", () => {
  it("has labels for all 3 speeds", () => {
    expect(Object.keys(ANIMATION_SPEED_LABELS)).toHaveLength(3);
  });

  it("maps all speeds correctly", () => {
    expect(ANIMATION_SPEED_LABELS[AnimationSpeed.SLOW]).toBe("Slow");
    expect(ANIMATION_SPEED_LABELS[AnimationSpeed.MEDIUM]).toBe("Medium");
    expect(ANIMATION_SPEED_LABELS[AnimationSpeed.FAST]).toBe("Fast");
  });
});
