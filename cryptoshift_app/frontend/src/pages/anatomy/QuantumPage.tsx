import { Link } from "react-router-dom";
import { PageHeader, Badge } from "../../components/ui";
import { QuantumFigure } from "../../figures/quantum/QuantumFigure";

export default function QuantumPage() {
  return (
    <>
      <PageHeader
        title="Anatomy of a Quantum Computer"
        subtitle="One quantum-computing platform — superconducting qubits — taken apart to show why it needs the machinery it does, and why that matters for the cryptography in your repositories."
        actions={<Badge tone="blue">Educational model · not application data</Badge>}
      />
      <QuantumFigure />
      <section className="card explainer" style={{ marginTop: 16 }} aria-labelledby="why-crypto">
        <h2 id="why-crypto" style={{ fontSize: 16, marginBottom: 8 }}>
          Why quantum computing matters for cryptography
        </h2>
        <div className="grid grid-2">
          <p>
            RSA, elliptic-curve Diffie–Hellman and ECDSA rely on factoring and discrete logarithms being infeasible. Shor's algorithm solves both efficiently on a sufficiently large, <strong>fault-tolerant</strong> quantum computer, so such a machine could recover private keys from public ones. Symmetric ciphers and hashes are affected far less: Grover's algorithm only offers a square-root speed-up, which is why AES-256 is generally considered adequate.
          </p>
          <p>
            Today's quantum computers are small and noisy and cannot break RSA or elliptic-curve keys at practical sizes; that would need error-corrected logical qubits at a scale not yet demonstrated, and estimates of when it might happen vary widely. The reason to migrate now is that data recorded today can be decrypted later ("harvest now, decrypt later"), and that inventorying and replacing cryptography across banking systems takes years.
          </p>
        </div>
        <div className="kv" style={{ marginTop: 12 }}>
          <Link className="btn btn-primary" to="/anatomy/cryptographic-asset">
            Explore CryptoShift's migration workflow
          </Link>
          <span className="small muted">Inventory → risk → plan → candidate patch → verification → human approval</span>
        </div>
      </section>
    </>
  );
}
