import * as React from "react";
import { AnatomyFrame, type PartInfo } from "../../anatomy/AnatomyFrame";
import { QuantumScene, W, H, anchorOf } from "./QuantumArt";
import { PARTS, STAGES, type QId } from "./model";

const SCENE = <QuantumScene key="scene" />;

export function QuantumFigure() {
  const [selected, setSelected] = React.useState<string | null>("chip");
  const parts: PartInfo[] = PARTS.map((p) => ({ id: p.id, label: p.label, summary: p.summary, readout: p.readout, anchor: anchorOf(p.id), related: p.related, status: "neutral" }));
  const sel = PARTS.find((p) => p.id === selected);
  return (
    <AnatomyFrame
      fig="Fig 01"
      title="Quantum computer"
      ariaLabel="Cutaway of a superconducting quantum computer: a dilution refrigerator with control and readout wiring, and its room-temperature electronics"
      width={W}
      height={H}
      parts={parts}
      selected={selected}
      onSelect={setSelected}
      idleReadout="educational model"
      hint="Select a component"
      keys={[
        { mark: "lit", label: "Quantum processor chip" },
        { mark: "raised", label: "Cryostat stage (smaller = colder)" },
        { mark: "edge", label: "Coaxial line" },
      ]}
      caption={<span>Educational model of one platform — superconducting qubits in a dilution refrigerator. Other platforms (trapped ions, neutral atoms, photonics) look very different. Shields are drawn removed so the stages are visible.</span>}
      detail={
        sel ? (
          <>
            <h3>{sel.label}</h3>
            <p>{sel.detail}</p>
            {sel.id === "cryostat" ? <StageTable /> : null}
            {sel.related?.length ? <p className="small muted">Connected: {sel.related.map((r) => PARTS.find((p) => p.id === (r as QId))!.label).join(", ")}</p> : null}
          </>
        ) : (
          <p className="muted">Select a component to see what it does.</p>
        )
      }
    >
      {SCENE}
    </AnatomyFrame>
  );
}

function StageTable() {
  return (
    <table>
      <thead>
        <tr>
          <th>Stage</th>
          <th>Typical</th>
        </tr>
      </thead>
      <tbody>
        {STAGES.map((s) => (
          <tr key={s.name}>
            <td>
              {s.name}
              <div className="small muted">{s.note}</div>
            </td>
            <td className="mono">{s.temp}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
