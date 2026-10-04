import { matchLabel, scoreTitle } from "../match";

/** Match strength in words, with a thin bar; the raw score is in the tooltip. */
export default function MatchMeter({ confidence, cited = false, compact = false }: { confidence: number; cited?: boolean; compact?: boolean }) {
  const m = matchLabel(confidence, cited);
  return (
    <div className={`meter meter-${m.tone}${compact ? " meter-compact" : ""}`} title={scoreTitle(confidence)}>
      <span className="meter-label">{m.label}</span>
      {!compact && <span className="meter-bar"><span style={{ width: `${Math.round(Math.min(1, confidence) * 100)}%` }} /></span>}
    </div>
  );
}
