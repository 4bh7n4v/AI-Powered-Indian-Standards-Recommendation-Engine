/**
 * Turns the engine's confidence score into words an official understands.
 *
 * The score is NOT a probability: it is BM25 term coverage x query specificity (or the dense
 * similarity when BGE-M3 is on). The engine already abstains below ABSTAIN_THRESHOLD = 0.30, so any
 * result that reaches the UI scored at least 0.30. An IS number typed by the user ("cited in input")
 * always comes back with confidence 1.0.
 *
 * The raw score stays available on hover (see `scoreTitle`), so the words never hide the number.
 */
export type MatchTone = "strong" | "possible" | "weak";

export interface MatchLabel {
  label: string; // shown on the card, e.g. "Strong match"
  tone: MatchTone; // colours the label and the bar
}

export function matchLabel(confidence: number, citedInInput = false): MatchLabel {
  // TODO(human): map confidence (0.30–1.00 after abstention) and citedInInput to a label + tone.
  // Temporary placeholder so the app builds; replace it with your own rule.
  return { label: citedInInput ? "Cited in input" : `${Math.round(confidence * 100)}% match`, tone: "possible" };
}

export const scoreTitle = (confidence: number) =>
  `Score ${confidence.toFixed(2)} (keyword coverage × specificity; not a probability)`;
