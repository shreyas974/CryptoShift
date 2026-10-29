import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PipelineFigure } from "../components/PipelineFigure";

const services = [
  { id: "interbank_tls", wave: 0, state: "READY" },
  { id: "ledger_audit", wave: 0, state: "PROPOSED" },
  { id: "card_vault", wave: 2, state: "READY" },
];

describe("PipelineFigure (anatomy kit)", () => {
  it("is an accessible image whose readout comes only from props", () => {
    const { container } = render(
      <PipelineFigure
        services={services}
        findings={14}
        objective={299.1}
        readyCount={2}
        approvedCount={0}
        theme="dark"
        reduceMotion
      />,
    );
    const img = screen.getByRole("img");
    expect(img.getAttribute("aria-label")).toContain("3 service crates in 3 scheduled waves");
    expect(img.getAttribute("aria-label")).toContain("2 of 3 steps are READY; 0 approved");
    // the first service in wave order is shown first: interbank_tls (wave 0, READY)
    expect(container.querySelector("[data-readout]")?.textContent).toBe(
      "interbank_tls · wave 0 · READY · 2/3 ready · objective 299.1",
    );
    expect(container.querySelectorAll(".pl-crate")).toHaveLength(3);
    expect(container.querySelector("style")).toBeNull(); // CSP: no inline <style> elements
    expect(screen.getByText(/Decorative explanation, not evidence/)).toBeInTheDocument();
  });

  it("keeps the gate boom down when the selected step is not READY and never invents a state", () => {
    const { container } = render(
      <PipelineFigure
        services={[{ id: "x", wave: 0, state: "" }]}
        findings={0}
        objective={null}
        readyCount={0}
        approvedCount={0}
        theme="light"
        reduceMotion
      />,
    );
    expect(container.querySelector("[data-readout]")?.textContent).toBe(
      "x · wave 0 · UNKNOWN · 0/1 ready · objective –",
    );
    const boom = container.querySelector(".pl-boom") as SVGGElement;
    expect(boom.style.transform).toBe("translate(0px, 0px)");
    expect(container.querySelector(".pl-figure")?.getAttribute("data-theme")).toBe("light");
  });
});
