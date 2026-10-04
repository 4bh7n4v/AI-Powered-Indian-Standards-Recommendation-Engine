import type { Health } from "../types";

interface Props {
  health: Health | null;
  lang: "en" | "hi";
  onLang: (l: "en" | "hi") => void;
}

export default function Header({ health, lang, onLang }: Props) {
  return (
    <header className="header">
      <div className="container header-inner">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">IS</span>
          <div>
            <h1>Indian Standards Recommendation Engine</h1>
            <p className="subtitle">Check procurement specifications against Indian Standards · SIH PS 26108</p>
          </div>
        </div>
        <div className="header-side">
          <div className="segmented" role="group" aria-label="Language of generated clauses">
            <button className={lang === "en" ? "on" : ""} onClick={() => onLang("en")} title="Clauses in English">EN</button>
            <button className={lang === "hi" ? "on" : ""} onClick={() => onLang("hi")} title="Clauses in Hindi">हिन्दी</button>
          </div>
          <span className={health ? "status ok" : "status down"} title={health ? `Retrieval: ${health.retrieval_mode} · ${health.dense}` : ""}>
            <span className="dot" />
            {health ? `Online · ${health.standards} standards` : "Engine offline"}
          </span>
        </div>
      </div>
    </header>
  );
}
