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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="panel max-w-md w-full rounded-[1.75rem] p-6 sm:p-8">
        <h2 className="section-title text-lg font-semibold mb-1">Before you continue</h2>
        <p className="section-copy text-sm mb-5">
          Vuclear generates synthetic speech from voice samples. You must agree to use this responsibly.
        </p>

        <ul className="space-y-2.5 mb-6">
          {TERMS.map((term) => (
            <li key={term} className="flex items-start gap-2.5 text-sm section-copy">
              <span className="theme-toggle__icon shrink-0 mt-0.5 !w-5 !h-5 !text-xs" aria-hidden="true">
                ✓
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
