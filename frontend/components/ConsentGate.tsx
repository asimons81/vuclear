"use client";

import { useAppStore } from "@/lib/store";

const TERMS = [
  "Only clone voices you own or have explicit written permission to use.",
  "Do not use generated audio to deceive, impersonate, or harm others.",
  "Outputs generated with the Chatterbox engine include a perceptual watermark.",
  "You are fully responsible for all content you generate.",
];

export default function ConsentGate({ children }: { children: React.ReactNode }) {
  const { tosAccepted, acceptTos } = useAppStore();

  if (tosAccepted) return <>{children}</>;

  return (
    <div className="consent-overlay fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="panel max-w-md w-full rounded-2xl p-6 sm:p-8">
        <h2 className="section-title text-lg font-semibold mb-1">Before you continue</h2>
        <p className="section-copy text-sm mb-5">
          Vuclear generates synthetic speech from voice samples. You must agree to use this responsibly.
        </p>

        <ul className="space-y-2.5 mb-6">
          {TERMS.map((term) => (
            <li key={term} className="flex items-start gap-2.5 text-sm section-copy">
              <span
                className="shrink-0 mt-0.5 w-5 h-5 rounded-full inline-flex items-center justify-center"
                style={{ background: "var(--accent-glow)", border: "1px solid color-mix(in srgb, var(--accent) 28%, transparent)", color: "var(--accent)" }}
                aria-hidden="true"
              >
                <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                  <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              {term}
            </li>
          ))}
        </ul>

        <p className="hint text-xs mb-6">For legitimate creative, accessibility, and research use only.</p>

        <button onClick={acceptTos} className="btn-primary w-full rounded-xl py-2.5 text-sm font-semibold">
          Accept and continue
        </button>
      </div>
    </div>
  );
}
