"use client";

import { useAppStore } from "@/lib/store";

export default function ConsentGate({ children }: { children: React.ReactNode }) {
  const { tosAccepted, acceptTos } = useAppStore();

  if (tosAccepted) return <>{children}</>;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="max-w-lg w-full bg-white rounded-2xl shadow-2xl p-8">
        <h2 className="text-2xl font-bold mb-4 text-gray-900">Before You Continue</h2>
        <div className="prose prose-sm text-gray-700 mb-6 space-y-3">
          <p>
            <strong>Voice Cloner</strong> lets you create synthetic speech that sounds like a
            specific person. This technology must only be used responsibly.
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>You may only clone a voice you own or have explicit written permission to clone.</li>
            <li>Do not use generated audio to deceive, impersonate, or harm anyone.</li>
            <li>Outputs may contain a perceptual watermark (Chatterbox engine).</li>
            <li>By continuing, you agree to these terms and take full responsibility for your use.</li>
          </ul>
          <p className="text-xs text-gray-500">
            This software is provided for legitimate creative, accessibility, and research use only.
          </p>
        </div>
        <button
          onClick={acceptTos}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          aria-label="Accept terms and continue to Voice Cloner"
        >
          I Understand — Continue
        </button>
      </div>
    </div>
  );
}
