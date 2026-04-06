"use client";

const MAX_CHARS = 50000;

type Props = {
  value: string;
  onChange: (value: string) => void;
};

export default function ScriptEditor({ value, onChange }: Props) {
  const remaining = MAX_CHARS - value.length;
  const pct = Math.round((value.length / MAX_CHARS) * 100);
  const isLow = remaining < 100;

  return (
    <div className="space-y-1.5">
      <label htmlFor="script-editor" className="label block text-sm font-medium">
        Script
      </label>
      <textarea
        id="script-editor"
        value={value}
        onChange={(e) => onChange(e.target.value.slice(0, MAX_CHARS))}
        rows={8}
        placeholder="Type or paste the text you want to synthesize..."
        className="field w-full rounded-2xl p-3 text-sm font-mono resize-y"
        aria-label="Script text editor"
        aria-describedby="script-counter"
      />
      <div id="script-counter" className="flex justify-between text-xs" aria-live="polite" aria-atomic="true">
        <span className={isLow ? "font-semibold" : "hint"} style={isLow ? { color: "var(--danger-text)" } : undefined}>
          {remaining.toLocaleString()} characters remaining
        </span>
        <span className="hint font-mono">{pct}%</span>
      </div>
      <div className="progress-track h-1.5 rounded-full overflow-hidden" aria-hidden="true">
        <div
          className="h-full transition-all duration-300"
          style={{
            width: `${pct}%`,
            background: pct > 90 ? "var(--danger-text)" : "linear-gradient(90deg, var(--accent-strong), var(--accent))",
          }}
        />
      </div>
    </div>
  );
}
