const STEPS = [
  {
    n: "1",
    title: "Ask in plain language",
    text: "Type a question the way you would ask a teacher. No special syntax needed.",
  },
  {
    n: "2",
    title: "The AI reads your course material",
    text: "It looks through the documents uploaded by your instructors and finds the relevant parts.",
  },
  {
    n: "3",
    title: "Get a clear, grounded answer",
    text: "You receive a simple explanation, and you can see which document it came from.",
  },
];

const FEATURES = [
  {
    icon: "📚",
    title: "Answers from your course",
    text: "Responses are based on your institute's own documents, not guesses from the internet.",
  },
  {
    icon: "💬",
    title: "Remembers the conversation",
    text: "Ask follow-up questions and come back later. Your past conversations are saved.",
  },
  {
    icon: "🧮",
    title: "Helps with calculations",
    text: "Switch to Agent mode and the AI can use a calculator and search tools for you.",
  },
];

export default function Home({ go }) {
  return (
    <>
      <section className="hero">
        <div className="container hero-grid">
          <div className="hero-copy">
            <span className="badge">✨ Your personal AI study buddy</span>
            <h1>
              Understand your course,
              <br />
              <em>one question at a time.</em>
            </h1>
            <p className="lead">
              An AI tutor that answers from your own course material, so you can learn faster
              and trust what you read.
            </p>
            <ul className="hero-points">
              <li>✓ Ask any time, day or night</li>
              <li>✓ Answers from your own course</li>
              <li>✓ Simple, clear explanations</li>
            </ul>
            <div className="hero-actions">
              <button className="btn btn-primary btn-lg" onClick={() => go("ask")}>
                Ask a question
              </button>
              <button className="btn btn-outline btn-lg" onClick={() => go("library")}>
                Browse the library
              </button>
            </div>
          </div>

          <div className="hero-visual" aria-hidden="true">
            <div className="float f1">📘 Python</div>
            <div className="float f2">🧠 Quiz me</div>
            <div className="float f3">⚡ Instant answers</div>
            <div className="mock">
              <div className="mock-bar">
                <i /> <i /> <i />
                <span>VPRO AI Tutor</span>
              </div>
              <div className="mock-body">
                <div className="bubble user">What is a Python list?</div>
                <div className="bubble ai">
                  A list is an ordered, changeable collection of items written inside square
                  brackets, for example <code>[1, 2, 3]</code>.
                  <span className="source">Source: Python Basics.pdf</span>
                </div>
                <div className="bubble user">And what is 250 × 4 + 150?</div>
                <div className="bubble ai">
                  That equals <b>1150</b>.<span className="tool">Used: Calculator</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-head">
            <span className="kicker">How it works</span>
            <h2>Three simple steps</h2>
          </div>
          <div className="steps">
            {STEPS.map((step) => (
              <div className="step" key={step.n}>
                <span className="step-n">{step.n}</span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-tint">
        <div className="container">
          <div className="section-head">
            <span className="kicker">Why students use it</span>
            <h2>Built to help you learn</h2>
          </div>
          <div className="cards-3">
            {FEATURES.map((feature) => (
              <div className="card feature" key={feature.title}>
                <span className="feature-icon">{feature.icon}</span>
                <h3>{feature.title}</h3>
                <p>{feature.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="cta-band">
            <div>
              <h2>Ready to try it?</h2>
              <p>Ask your first question. It takes a few seconds.</p>
            </div>
            <button className="btn btn-light btn-lg" onClick={() => go("ask")}>
              Start asking
            </button>
          </div>
        </div>
      </section>
    </>
  );
}