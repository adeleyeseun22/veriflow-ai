import { SystemCheck } from "@/components/system-check";

const capabilities = [
  {
    index: "01",
    title: "Evidence-grounded answers",
    text: "Retrieve organizational knowledge and connect every material claim to its precise source.",
  },
  {
    index: "02",
    title: "Data validation",
    text: "Recalculate reported figures and compare narrative statements with structured records.",
  },
  {
    index: "03",
    title: "Contradiction intelligence",
    text: "Surface conflicting facts while accounting for document dates and version history.",
  },
];

export default function Home() {
  return (
    <main>
      <nav className="nav-shell">
        <a className="brand" href="#top" aria-label="VeriFlow AI home">
          <span className="brand-mark">V</span>
          <span>VeriFlow AI</span>
        </a>

        <span className="phase-badge">Phase 0 · Foundation</span>
      </nav>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">Evidence-first artificial intelligence</p>

          <h1>Turn scattered information into decisions you can defend.</h1>

          <p className="hero-description">
            VeriFlow AI ingests documents and structured data, retrieves the strongest evidence,
            validates numerical claims, detects contradictions, and preserves a reviewable audit
            trail.
          </p>

          <div className="hero-actions">
            <a className="primary-button link-button" href="#foundation">
              Inspect foundation
            </a>

            <a className="secondary-button" href="http://localhost:8000/docs">
              Open API documentation
            </a>
          </div>
        </div>

        <div className="hero-visual" aria-label="VeriFlow evidence flow diagram">
          <div className="signal signal-one" />
          <div className="signal signal-two" />

          <div className="core-orb">
            <span>VF</span>
          </div>

          <div className="orbit orbit-one">
            <span>Documents</span>
          </div>

          <div className="orbit orbit-two">
            <span>Evidence</span>
          </div>

          <div className="orbit orbit-three">
            <span>Decisions</span>
          </div>
        </div>
      </section>

      <section className="capability-grid" aria-label="Core product capabilities">
        {capabilities.map((capability) => (
          <article className="capability-card" key={capability.index}>
            <span className="card-index">{capability.index}</span>
            <h2>{capability.title}</h2>
            <p>{capability.text}</p>
          </article>
        ))}
      </section>

      <section className="foundation" id="foundation">
        <div className="section-heading">
          <p className="eyebrow">Production foundation</p>
          <h2>Four services. One reproducible local environment.</h2>
        </div>

        <div className="service-grid">
          <ServiceCard name="Next.js" role="Product interface" endpoint=":3000" />
          <ServiceCard name="FastAPI" role="Application API" endpoint=":8000" />
          <ServiceCard name="PostgreSQL" role="Data + pgvector" endpoint=":5432" />
          <ServiceCard name="Redis" role="Cache + job layer" endpoint=":6379" />
        </div>

        <SystemCheck />
      </section>

      <footer>
        <span>VeriFlow AI</span>
        <span>Multimodal evidence and decision intelligence</span>
      </footer>
    </main>
  );
}

function ServiceCard({
  name,
  role,
  endpoint,
}: {
  name: string;
  role: string;
  endpoint: string;
}) {
  return (
    <article className="service-card">
      <div className="service-dot" />

      <div>
        <strong>{name}</strong>
        <span>{role}</span>
      </div>

      <code>{endpoint}</code>
    </article>
  );
}