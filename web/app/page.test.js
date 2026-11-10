import { describe, expect, test } from "bun:test";
import { benchRiskLabel, getApiBase, getVisibleLivePoint, stepMockPointToward } from "./page.tsx";

describe("getApiBase", () => {
  test("uses the bridge on local development hosts by default", () => {
    expect(getApiBase(undefined, "localhost")).toBe("http://localhost:8888");
    expect(getApiBase(undefined, "127.0.0.1")).toBe("http://localhost:8888");
  });

  test("does not point deployed browsers at their own localhost", () => {
    expect(getApiBase(undefined, "balat-vercel.app")).toBe("");
  });

  test("respects an explicitly configured bridge URL", () => {
    expect(getApiBase("https://bridge.example.test/", "balat-vercel.app")).toBe("https://bridge.example.test");
  });
});

describe("stepMockPointToward", () => {
  test("caps a 100 ms BLE mock movement to about 50 cm at 5 m/s", () => {
    const next = stepMockPointToward({ x_cm: 0, y_cm: 0 }, { x_cm: 1000, y_cm: 0 }, 100);
    expect(next.x_cm).toBe(50);
    expect(next.y_cm).toBe(0);
  });

  test("keeps diagonal movement within the 5 m/s distance cap", () => {
    const next = stepMockPointToward({ x_cm: 0, y_cm: 0 }, { x_cm: 1000, y_cm: 1000 }, 100);
    expect(Math.hypot(next.x_cm, next.y_cm)).toBeLessThanOrEqual(50);
  });

  test("snaps to the target when it is within the allowed step", () => {
    expect(stepMockPointToward({ x_cm: 0, y_cm: 0 }, { x_cm: 20, y_cm: 0 }, 100)).toEqual({ x_cm: 20, y_cm: 0 });
  });
});

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
