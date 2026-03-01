"use client";

const MAX_CHARS = 2000;

type Props = {
  value: string;
  onChange: (v: string) => void;
};

export default function ScriptEditor({ value, onChange }: Props) {
  const remaining = MAX_CHARS - value.length;
  const pct = Math.round((value.length / MAX_CHARS) * 100);

  return (
    <div className="space-y-2">
      <label htmlFor="script-editor" className="block text-sm font-medium text-gray-700">
        Script
      </label>
      <textarea
        id="script-editor"
        value={value}
        onChange={(e) => onChange(e.target.value.slice(0, MAX_CHARS))}
        rows={8}
        placeholder="Type or paste the text you want to generate…"
        className="w-full border border-gray-300 rounded-lg p-3 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        aria-label="Script text editor"
        aria-describedby="script-counter"
      />
      <div
        id="script-counter"
        className="flex justify-between text-xs"
        aria-live="polite"
        aria-atomic="true"
      >
        <span className={remaining < 100 ? "text-orange-600 font-medium" : "text-gray-500"}>
          {remaining.toLocaleString()} characters remaining
        </span>
        <span className="text-gray-400">{pct}%</span>
      </div>
      {/* Progress bar */}
      <div className="h-1 bg-gray-200 rounded-full overflow-hidden" aria-hidden="true">
        <div
          className={`h-full transition-all ${pct > 90 ? "bg-orange-500" : "bg-indigo-400"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
