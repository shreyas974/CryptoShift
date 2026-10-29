// Educational model of ONE platform: a superconducting-qubit system in a dilution refrigerator.
// Temperatures are typical published figures for such systems, not measurements of a specific machine.
export type QId = "cryostat" | "io" | "control" | "attenuators" | "readout" | "package" | "chip" | "control-electronics" | "readout-electronics" | "computer" | "shielding";

export interface QPart {
  id: QId;
  label: string;
  summary: string;
  readout: string;
  detail: string;
  related?: QId[];
}

export const STAGES = [
  { name: "Top flange", temp: "≈ 300 K", note: "Room temperature; vacuum feedthroughs" },
  { name: "50 K plate", temp: "≈ 50 K", note: "First pulse-tube stage" },
  { name: "4 K plate", temp: "≈ 4 K", note: "Second pulse-tube stage; readout amplifier" },
  { name: "Still", temp: "≈ 0.8 K", note: "Helium-3 is distilled here" },
  { name: "Cold plate", temp: "≈ 0.1 K", note: "Intermediate thermalisation" },
  { name: "Mixing chamber", temp: "≈ 10 mK", note: "Coldest stage; the chip is mounted below it" },
];

export const PARTS: QPart[] = [
  {
    id: "cryostat",
    label: "Dilution refrigerator / cryostat",
    summary: "Nested stages cool from room temperature to about 10 millikelvin.",
    readout: "300 K → 10 mK",
    detail: "Superconducting qubits only behave quantum-mechanically when thermal noise is far below their transition energy, so the processor sits at the bottom of a dilution refrigerator. Each plate is a colder stage; the plates shrink as they get colder.",
    related: ["shielding"],
  },
  { id: "io", label: "Input / output connections", summary: "Hermetic coaxial feedthroughs carry signals through the room-temperature flange.", readout: "300 K feedthroughs", detail: "Every control and readout signal enters and leaves through sealed connectors on the top flange, so the vacuum stays intact.", related: ["control", "readout"] },
  { id: "control", label: "Microwave control lines", summary: "Shaped microwave pulses travel down to drive individual qubits.", readout: "pulses ↓ to the chip", detail: "Gate operations are microwave pulses a few tens of nanoseconds long, generated at room temperature and carried down on coaxial lines.", related: ["attenuators", "io", "chip"] },
  { id: "attenuators", label: "Attenuators and filters", summary: "Each stage attenuates and filters the control lines so room-temperature noise never reaches the qubits.", readout: "attenuation per stage", detail: "Attenuators at successive stages absorb thermal noise from warmer stages; filters near the mixing chamber block stray high-frequency radiation.", related: ["control"] },
  { id: "readout", label: "Readout lines", summary: "Weak signals travel up through isolators and a cryogenic amplifier.", readout: "signal ↑ to amplifiers", detail: "Qubit states are measured with resonators. The faint response passes isolators that block back-travelling noise, then a low-noise amplifier on the 4 K plate.", related: ["io", "readout-electronics"] },
  { id: "package", label: "Qubit chip package", summary: "A shielded holder on a cold finger anchors the chip thermally to the mixing chamber.", readout: "≈ 10 mK", detail: "The package provides the chip's microwave environment and wiring, and conducts its heat to the coldest stage.", related: ["chip"] },
  { id: "chip", label: "Quantum processor chip", summary: "Superconducting circuits whose states are the qubits.", readout: "qubits", detail: "Josephson-junction circuits patterned on the chip act as qubits and couplers. This is the part every other component exists to serve.", related: ["package", "control", "readout"] },
  { id: "control-electronics", label: "Control electronics", summary: "Room-temperature instruments synthesise the microwave control pulses.", readout: "pulse synthesis", detail: "Arbitrary-waveform generators and mixers create the pulse sequences that implement gates.", related: ["control", "computer"] },
  { id: "readout-electronics", label: "Readout electronics", summary: "Digitise and demodulate the amplified readout signal into measurement results.", readout: "digitise → 0 / 1", detail: "The returning signal is mixed down, digitised and classified as a measurement outcome for each qubit.", related: ["readout", "computer"] },
  { id: "computer", label: "Classical control computer", summary: "Compiles programs into pulse schedules and collects results.", readout: "compile · schedule · collect", detail: "Every quantum computation is orchestrated by classical software; error correction at scale would also need fast classical decoding.", related: ["control-electronics", "readout-electronics"] },
  { id: "shielding", label: "Shielding and structural mounts", summary: "Support frame plus radiation and magnetic shields (shown removed for this cutaway).", readout: "shield removed for view", detail: "In operation, nested cans enclose every stage to block thermal radiation and magnetic fields. One is drawn standing beside the frame so the stages stay visible.", related: ["cryostat"] },
];
