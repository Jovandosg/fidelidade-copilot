import { describe, expect, it } from "vitest";
import { fmtPct, splitDrivers } from "./format";

describe("format", () => {
  it("separa fatores de risco", () => {
    expect(splitDrivers("nivel de fidelidade; atraso medio elevado")).toEqual(["nivel de fidelidade", "atraso medio elevado"]);
    expect(splitDrivers("")).toEqual([]);
  });

  it("percentual sem divisao por zero", () => {
    expect(fmtPct(1, 0)).toBe("0%");
    expect(fmtPct(1, 4)).toBe("25%");
  });
});
