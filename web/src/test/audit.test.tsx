/** Regression tests for the user-audit fixes (docs/USER_AUDIT_AND_FIX_REPORT.md). */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge } from "../components/ui";
import { isPass, normStatus } from "../lib/status";
import { Certainty, missingGate } from "../pages/tier1";

describe("gates that were not evaluated", () => {
  it("are NOT RUN while the purpose is unresolved", () => {
    const s = {
      gates: [
        { gate: "purpose_resolved", status: "FAIL" },
        { gate: "rollback_rehearsal", status: "PASS" },
      ],
    };
    expect(missingGate(s).status).toBe("NOT RUN");
  });
  it("are NOT APPLICABLE once the purpose is resolved", () => {
    const s = { gates: [{ gate: "purpose_resolved", status: "PASS" }] };
    expect(missingGate(s).status).toBe("NOT APPLICABLE");
  });
  it("are never counted as a pass", () => {
    for (const v of ["NOT RUN", "NOT APPLICABLE", "not run"]) expect(isPass(v)).toBe(false);
    expect(normStatus("not applicable")).toBe("NOT APPLICABLE");
    render(<Badge value="NOT RUN" />);
    expect(screen.getByText("NOT RUN")).toBeTruthy();
  });
});

describe("finding role certainty", () => {
  it("shows UNKNOWN / MANUAL REVIEW as its own state, never as confirmed", () => {
    render(<Certainty value="UNKNOWN / MANUAL REVIEW" />);
    const el = screen.getByText("UNKNOWN / MANUAL REVIEW");
    expect(el.closest(".badge")?.className).not.toContain("t-ok");
  });
});
