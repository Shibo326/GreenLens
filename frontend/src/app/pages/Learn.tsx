import { Link } from "react-router";
import { NavigationBar } from "../components/NavigationBar";
import { PrimaryButton, GhostButton } from "../components/Buttons";

const sins = [
  {
    number: 1,
    title: "Hidden Trade-Off",
    description:
      "Highlighting one green thing while hiding bigger environmental harm. Companies cherry-pick a single eco-friendly attribute to distract from the much larger damage their product or process causes.",
    example:
      "'Made with recycled paper' from a factory that pumps toxic waste into rivers",
    spotIt:
      "If they only mention ONE attribute, ask what they're NOT telling you",
  },
  {
    number: 2,
    title: "No Proof",
    description:
      "Making green claims with zero evidence you can check. No certifications, no data, no third-party audits — just words designed to make you feel good about buying.",
    example:
      "'50% less plastic' — but where's the data? Where's the certification?",
    spotIt:
      "No link to a report, no third-party logo, no verifiable number = no proof",
  },
  {
    number: 3,
    title: "Vagueness",
    description:
      "Using words that sound green but mean nothing. These terms have no legal or scientific definition, so companies can slap them on anything without accountability.",
    example:
      "'All-natural', 'eco-friendly', 'green', 'clean' — none of these have legal definitions",
    spotIt:
      "If you can't measure it or verify it against a standard, it's vague",
  },
  {
    number: 4,
    title: "Irrelevance",
    description:
      "Technically true, but completely useless information. The claim might be accurate but refers to something that's already legally required or universally true.",
    example:
      "'CFC-free!' — CFCs have been banned since 1987. Everything is CFC-free.",
    spotIt:
      "Is this claim about something that's already legally required?",
  },
  {
    number: 5,
    title: "Lesser of Two Evils",
    description:
      "Being the 'greenest' option in a terrible category. It distracts from the fundamental problem with the product category itself.",
    example:
      "'Eco-friendly SUV' or 'organic cigarettes' — still an SUV, still cigarettes",
    spotIt:
      "Ask whether the PRODUCT CATEGORY itself is the problem, not just this version",
  },
  {
    number: 6,
    title: "Fibbing",
    description:
      "Straight-up lying about environmental credentials. Fabricated claims, fake data, or certifications the product never actually received.",
    example:
      "Claiming Energy Star certification when the product was never certified",
    spotIt:
      "Google the certification + company name. If it's not in the official registry, it's fake",
  },
  {
    number: 7,
    title: "False Labels",
    description:
      "Fake logos designed to look like real certifications. These visual tricks exploit trust in official-looking badges to mislead consumers.",
    example:
      "A green leaf logo that looks official but links to the company's own website",
    spotIt:
      "Real certifications have searchable public registries. If you can't look it up, it's fake",
  },
];

export default function Learn() {
  return (
    <div className="min-h-screen" style={{ background: "var(--ink)" }}>
      <NavigationBar />

      {/* Title Section */}
      <section
        className="flex flex-col items-center text-center px-4 sm:px-6 mx-auto"
        style={{ maxWidth: "1200px", paddingTop: "48px", paddingBottom: "32px" }}
      >
        <h1
          style={{
            fontFamily: "'Syne', 'DM Sans', sans-serif",
            fontWeight: 800,
            fontSize: "clamp(28px, 5vw, 42px)",
            color: "var(--paper)",
            marginBottom: "12px",
            letterSpacing: "-0.02em",
          }}
        >
          Learn: The 7 Sins of Greenwashing
        </h1>
        <p
          style={{
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontWeight: 400,
            fontSize: "clamp(15px, 2.5vw, 17px)",
            color: "var(--ash)",
            maxWidth: "560px",
            lineHeight: 1.6,
          }}
        >
          Master these patterns and you'll spot greenwashing everywhere
        </p>
      </section>

      {/* Cards Grid */}
      <section
        className="px-4 sm:px-6 mx-auto pb-12"
        style={{ maxWidth: "1200px" }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 340px), 1fr))",
            gap: "24px",
          }}
        >
          {sins.map((sin) => (
            <div
              key={sin.number}
              style={{
                background: "var(--lead)",
                border: "1px solid var(--rule)",
                borderRadius: "12px",
                padding: "24px",
                position: "relative",
                display: "flex",
                flexDirection: "column",
                gap: "14px",
              }}
            >
              {/* Number badge */}
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "50%",
                  background: "var(--leaf)",
                  color: "var(--ink)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "'Syne', 'DM Sans', sans-serif",
                  fontWeight: 700,
                  fontSize: "14px",
                  flexShrink: 0,
                }}
              >
                {sin.number}
              </div>

              {/* Title */}
              <h3
                style={{
                  fontFamily: "'Syne', 'DM Sans', sans-serif",
                  fontWeight: 700,
                  fontSize: "18px",
                  color: "var(--paper)",
                  margin: 0,
                }}
              >
                {sin.title}
              </h3>

              {/* Description */}
              <p
                style={{
                  fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                  fontWeight: 400,
                  fontSize: "14px",
                  lineHeight: 1.6,
                  color: "var(--ash)",
                  margin: 0,
                }}
              >
                {sin.description}
              </p>

              {/* Example box */}
              <div
                style={{
                  background: "var(--graphite)",
                  borderRadius: "8px",
                  padding: "12px 14px",
                }}
              >
                <span
                  style={{
                    fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace",
                    fontSize: "13px",
                    lineHeight: 1.5,
                    color: "var(--paper)",
                    fontStyle: "italic",
                  }}
                >
                  {sin.example}
                </span>
              </div>

              {/* Spot it tip */}
              <p
                style={{
                  fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
                  fontWeight: 500,
                  fontSize: "13px",
                  lineHeight: 1.5,
                  color: "var(--leaf)",
                  margin: 0,
                  marginTop: "auto",
                }}
              >
                💡 {sin.spotIt}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section
        className="flex flex-col items-center text-center px-4 sm:px-6 mx-auto"
        style={{
          maxWidth: "1200px",
          paddingTop: "32px",
          paddingBottom: "64px",
        }}
      >
        <h2
          style={{
            fontFamily: "'Syne', 'DM Sans', sans-serif",
            fontWeight: 700,
            fontSize: "clamp(22px, 4vw, 28px)",
            color: "var(--paper)",
            marginBottom: "24px",
          }}
        >
          Ready to put this knowledge to use?
        </h2>
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <Link to="/">
            <PrimaryButton
              style={{
                height: "48px",
                padding: "12px 28px",
                fontSize: "15px",
                fontWeight: 600,
              }}
            >
              Scan a Document
            </PrimaryButton>
          </Link>
          <Link to="/demo">
            <GhostButton
              style={{
                height: "48px",
                padding: "12px 28px",
                fontSize: "15px",
                fontWeight: 600,
              }}
            >
              Try the Demo
            </GhostButton>
          </Link>
        </div>
      </section>
    </div>
  );
}
