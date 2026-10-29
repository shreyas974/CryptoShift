import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { EvidenceProvider } from "../components/evidence";
import { Badge, Evidence, ScannedText } from "../components/ui";
import { usePrefs } from "../lib/prefs";
import { badgeInfo, canApprove, isPass, normStatus, plainText } from "../lib/status";

describe("status badges", () => {
  it("never shows an unknown status as passed", () => {
    for (const v of ["passed", "ok", "", null, undefined, "Green", "READY!", "<b>PASS</b>"]) {
      expect(normStatus(v)).toBe("UNKNOWN");
      expect(isPass(v)).toBe(false);
    }
    render(<Badge value="totally-fine" />);
    const b = screen.getByText("UNKNOWN");
    expect(b.closest("[data-status]")).toHaveAttribute("data-status", "UNKNOWN");
  });
  it("always pairs an icon with text (never colour alone)", () => {
    for (const s of ["VERIFIED", "BLOCKED", "SIMULATOR", "OBSERVED", "INFERRED", "HOLD", "PLANNED"]) {
      const info = badgeInfo(s);
      expect(info.icon.length).toBeGreaterThan(0);
      expect(info.status).toBe(s);
    }
  });
});

describe("approval dialog logic", () => {
  const hash = "ab".repeat(32);
  const ready = { state: "READY", all_required_gates_pass: true };
  it("allows only READY + all gates + name + 12-char hash prefix + acknowledgement", () => {
    expect(canApprove(ready, "TEST-ONLY", hash.slice(0, 12), hash, true).ok).toBe(true);
  });
  it.each([
    [{ state: "PROPOSED", all_required_gates_pass: true }, "TEST-ONLY", hash.slice(0, 12), true],
    [{ state: "READY", all_required_gates_pass: false }, "TEST-ONLY", hash.slice(0, 12), true],
    [{ state: "maybe", all_required_gates_pass: true }, "TEST-ONLY", hash.slice(0, 12), true],
    [ready, "   ", hash.slice(0, 12), true],
    [ready, "TEST-ONLY", hash.slice(0, 8), true],
    [ready, "TEST-ONLY", "f".repeat(12), true],
    [ready, "TEST-ONLY", hash.slice(0, 12), false],
  ])("blocks %#", (step, name, typed, ack) => {
    expect(canApprove(step, name, typed, hash, ack).ok).toBe(false);
  });
  it("blocks when no plan hash is known", () => {
    expect(canApprove(ready, "TEST-ONLY", hash.slice(0, 12), null, true).ok).toBe(false);
  });
});

describe("escaped rendering of scanned text", () => {
  it("renders hostile strings as plain text and caps length", () => {
    const hostile = "<script>alert(1)</script><img src=x onerror=alert(2)>" + "x".repeat(10_000);
    const { container } = render(<ScannedText value={hostile} />);
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent?.startsWith("<script>")).toBe(true);
    expect((container.textContent ?? "").length).toBeLessThanOrEqual(160);
  });
  it("strips control characters", () => {
    expect(plainText("a\u001b[31mb\u0000c")).toBe("a [31mb c");
  });
});

describe("theme and fallback switches", () => {
  it("applies theme and accessibility classes to <html>", () => {
    const { result } = renderHook(() => usePrefs());
    act(() => result.current[1]({ theme: "light", reduceTransparency: true, highContrast: true, reduceMotion: true }));
    const el = document.documentElement;
    expect(el.dataset.theme).toBe("light");
    expect(el.classList.contains("reduce-transparency")).toBe(true);
    expect(el.classList.contains("high-contrast")).toBe(true);
    expect(el.classList.contains("reduce-motion")).toBe(true);
    act(() =>
      result.current[1]({ theme: "dark", reduceTransparency: false, highContrast: false, reduceMotion: false }),
    );
    expect(el.dataset.theme).toBe("dark");
    expect(el.classList.contains("high-contrast")).toBe(false);
  });
});

describe("evidence drawer", () => {
  it("opens with the source file, producer, SHA-256 and command", async () => {
    const src = {
      file: "reports/member3/plan.json",
      producer: "Member 3 pipeline",
      label: "VERIFIED on SYNTHETIC demo bank",
      command: "scripts/member3_pipeline.py",
      sha256: "abc123",
      modified: "2026-10-29T10:00:00",
    };
    render(
      <EvidenceProvider>
        <Evidence source={src} label="Findings">
          14
        </Evidence>
      </EvidenceProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Evidence for Findings" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("reports/member3/plan.json")).toBeInTheDocument();
    expect(screen.getByText("abc123")).toBeInTheDocument();
    expect(screen.getByText("scripts/member3_pipeline.py")).toBeInTheDocument();
  });
});
