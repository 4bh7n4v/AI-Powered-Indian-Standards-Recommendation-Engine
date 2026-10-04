/**
 * One status system for the whole app. Every state has a tone (colour), an icon and a word, so a
 * result never relies on colour alone (projectors wash out amber; some judges are colour-blind).
 */
import Icon, { type IconName } from "./components/Icon";
import type { Finding, ItemStatus, TenderStatus } from "./types";

export type Tone = "good" | "warn" | "bad" | "neutral" | "info";

interface StatusMeta { tone: Tone; icon: IconName; label: string }

export const STATUS: Record<TenderStatus | ItemStatus | "matched", StatusMeta> = {
  acceptable: { tone: "good", icon: "check", label: "Acceptable" },
  partially_acceptable: { tone: "warn", icon: "alert", label: "Partially acceptable" },
  needs_revision: { tone: "warn", icon: "alert", label: "Needs revision" },
  not_acceptable: { tone: "bad", icon: "cross", label: "Not acceptable" },
  not_applicable: { tone: "neutral", icon: "minus", label: "No applicable IS" },
  unreadable: { tone: "neutral", icon: "help", label: "Could not read" },
  matched: { tone: "info", icon: "search", label: "Standards found" },
};

export const SEVERITY: Record<Finding["severity"], StatusMeta> = {
  high: { tone: "bad", icon: "cross", label: "Missing / outdated" },
  medium: { tone: "warn", icon: "alert", label: "Incomplete" },
  low: { tone: "neutral", icon: "info", label: "Minor" },
  info: { tone: "neutral", icon: "help", label: "Check manually" },
};

/** Findings that point at something the tender should contain but doesn't. */
export const GAP_KINDS = new Set(["missing", "incomplete_test_method", "incomplete_safety", "certification_not_stated"]);

export function StatusPill({ status, label, size = "md" }: { status: keyof typeof STATUS; label?: string | null; size?: "sm" | "md" }) {
  const m = STATUS[status] ?? STATUS.not_applicable;
  return (
    <span className={`pill tone-${m.tone} pill-${size}`}>
      <Icon name={m.icon} size={size === "sm" ? 13 : 15} />
      {label ?? m.label}
    </span>
  );
}

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}
