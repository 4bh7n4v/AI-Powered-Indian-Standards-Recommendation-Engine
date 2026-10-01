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
        <div>
          <p className="eyebrow">Smart India Hackathon · Problem Statement 26108</p>
          <h1>Indian Standards Recommendation Engine</h1>
          <p className="subtitle">Identify applicable Indian Standards, allied standards and certification requirements for procurement specifications</p>
        </div>
        <div className="header-side">
          <label className="lang-select">
            <span>Output language</span>
            <select value={lang} onChange={(e) => onLang(e.target.value as "en" | "hi")}>
              <option value="en">English</option>
              <option value="hi">हिन्दी (Hindi)</option>
            </select>
          </label>
          <div className={health ? "status ok" : "status down"} title={health?.dense ?? ""}>
            <span className="dot" />
            {health ? `Engine online · ${health.standards} standards · data as of ${health.data_as_of}` : "Engine offline"}
          </div>
        </div>
      </div>
    </header>
  );
}
