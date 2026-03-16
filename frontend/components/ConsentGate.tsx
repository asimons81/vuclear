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
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 p-6 sm:p-8">
        <h2 className="text-lg font-semibold text-slate-900 mb-1">Before you continue</h2>
        <p className="text-sm text-slate-500 mb-5">
          Vuclear generates synthetic speech from voice samples. You must agree to use
          this responsibly.
        </p>

        <ul className="space-y-2.5 mb-6">
          {TERMS.map((term) => (
            <li key={term} className="flex items-start gap-2.5 text-sm text-slate-700">
              <span className="text-indigo-600 shrink-0 mt-0.5 font-medium" aria-hidden="true">
                ✓
              </span>
              {term}
            </li>
          ))}
        </ul>

        <p className="text-xs text-slate-400 mb-6">
          For legitimate creative, accessibility, and research use only.
        </p>

        <button
          onClick={acceptTos}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg transition-colors text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          Accept and continue
        </button>
      </div>
    </div>
  );
}
