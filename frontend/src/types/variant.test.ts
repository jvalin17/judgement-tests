import { DealingVariant, VARIANT_CONFIG, VARIANT_LIST } from "./game";

describe("Variant config consistency", () => {
  it("VARIANT_LIST contains all defined variants", () => {
    const variantValues = Object.values(DealingVariant);
    expect(VARIANT_LIST).toHaveLength(variantValues.length);
    for (const variant of variantValues) {
      expect(VARIANT_LIST).toContain(variant);
    }
  });

  it("every variant has a config entry", () => {
    for (const variant of VARIANT_LIST) {
      const config = VARIANT_CONFIG[variant];
      expect(config).toBeDefined();
      expect(config.label).toBeTruthy();
      expect(config.rounds).toBeTruthy();
      expect(config.detail).toBeTruthy();
      expect(config.maxPlayers).toBeGreaterThanOrEqual(2);
    }
  });

  it("maxPlayers is within reasonable bounds", () => {
    for (const variant of VARIANT_LIST) {
      const config = VARIANT_CONFIG[variant];
      expect(config.maxPlayers).toBeGreaterThanOrEqual(2);
      expect(config.maxPlayers).toBeLessThanOrEqual(52); // can't deal more than 52 cards
    }
  });

  it("label contains round count", () => {
    for (const variant of VARIANT_LIST) {
      const config = VARIANT_CONFIG[variant];
      expect(config.label).toContain("round");
    }
  });
});
