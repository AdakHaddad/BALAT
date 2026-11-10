import { describe, expect, test } from "bun:test";
import { benchRiskLabel, getVisibleLivePoint } from "./page.tsx";

describe("getVisibleLivePoint", () => {
  test("keeps the last reported point visible while marking its fix invalid", () => {
    expect(getVisibleLivePoint({
      fix_valid: false,
      seq: 1860,
      x_cm: 12038,
      y_cm: -1761,
    }, true)).toEqual({ x_cm: 12038, y_cm: -1761 });
  });

  test("does not invent a point before a fix has been reported", () => {
    expect(getVisibleLivePoint({
      fix_valid: false,
      seq: 0,
      x_cm: 0,
      y_cm: 0,
    }, true)).toBeNull();
  });

  test("does not show live points outside bench mode", () => {
    expect(getVisibleLivePoint({
      fix_valid: true,
      seq: 1,
      x_cm: 12,
      y_cm: 34,
    }, false)).toBeNull();
  });
});

describe("benchRiskLabel", () => {
  test("uses a clear wait state for an invalid active mock point", () => {
    expect(benchRiskLabel("INVALID", true)).toBe("WAITING FOR FIX");
  });

  test("keeps explicit invalid status outside active mock-point mode", () => {
    expect(benchRiskLabel("INVALID", false)).toBe("INVALID");
  });

  test("keeps valid risk states unchanged during mock-point mode", () => {
    expect(benchRiskLabel("DANGER", true)).toBe("DANGER");
  });
});
