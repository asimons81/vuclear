"use client";

const MAX_CHARS = 2000;

type Props = {
  value: string;
  onChange: (v: string) => void;
};

export default function ScriptEditor({ value, onChange }: Props) {
  const remaining = MAX_CHARS - value.length;
  const pct = Math.round((value.length / MAX_CHARS) * 100);
  const isLow = remaining < 100;

  return (
    <div className="space-y-1.5">
      <label htmlFor="script-editor" className="block text-sm font-medium text-slate-700">
        Script
      </label>
      <textarea
        id="script-editor"
        value={value}
        onChange={(e) => onChange(e.target.value.slice(0, MAX_CHARS))}
        rows={8}
        placeholder="Type or paste the text you want to synthesize…"
        className="w-full border border-slate-300 rounded-lg p-3 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        aria-label="Script text editor"
        aria-describedby="script-counter"
      />
      <div
        id="script-counter"
        className="flex justify-between text-xs"
        aria-live="polite"
        aria-atomic="true"
      >
        <span className={isLow ? "text-orange-600 font-medium" : "text-slate-400"}>
          {remaining.toLocaleString()} characters remaining
        </span>
        <span className="text-slate-400 font-mono">{pct}%</span>
      </div>
      <div className="h-1 bg-slate-200 rounded-full overflow-hidden" aria-hidden="true">
        <div
          className={`h-full transition-all duration-300 ${pct > 90 ? "bg-orange-500" : "bg-indigo-400"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
